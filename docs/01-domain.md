# 01 — Le domaine

> `src/domain/` — le centre de l'application. Il ne dépend de rien, tout dépend de lui.

## Ce qu'on y met, et ce qu'on n'y met pas

Le domaine répond à la question **« de quoi parle-t-on ? »**, jamais à **« comment on s'y prend ? »**.

Un député, une loi, une séance, le fait qu'un mandat sans date de fin est encore actif : ça, c'est du domaine. Télécharger un ZIP, gérer un namespace XML, écrire un `INSERT … ON CONFLICT` : ça ne l'est pas.

Le critère de tri, quand on hésite : **est-ce que ce serait encore vrai si on changeait complètement de source de données et de base ?** Si oui, c'est du domaine.

```
src/domain/
├── entities/        les choses dont parle le métier
├── ports/           les prises murales
└── shared/          le vocabulaire commun
```

## La règle de dépendance, et le test qui l'applique

> `src/domain/` n'importe jamais `src/infrastructure/`, `src/application/`, ni `src/interfaces/`.
> Il n'importe non plus aucune brique technique : ni `httpx`, ni `boto3`, ni `sqlalchemy`, ni `lxml`.

Une seule exception : **Pydantic**. Les entités décrivent des données venues de l'extérieur, il faut bien les valider quelque part. Pydantic décrit *une forme de donnée* ; `httpx` décrit *un mécanisme*. C'est là que passe la frontière.

Cette règle est vérifiée par `tests/unit/test_architecture.py`, qui lit l'arbre syntaxique de chaque fichier et ne regarde que les vrais imports — un `grep` remonterait aussi le mot « infrastructure » écrit dans un commentaire. Si ce test casse, **c'est le fichier qui est au mauvais endroit**, pas le test.

---

## `entities/` — les données du métier

Onze fichiers, un par notion. Ce sont des modèles Pydantic v2 : ils valident ce qui entre et ne font rien d'autre.

| Fichier | Ce que c'est | Particularité |
|---|---|---|
| `deputy.py` | une personne élue | porte ses `mandates` |
| `mandate.py` | son mandat dans une législature | `is_active` calculé depuis la date de fin |
| `political_group.py` | un groupe politique | ajouté en J1 : il manquait |
| `law.py` | un dossier législatif | `status`, `current_stage`, `is_promulgated` calculés depuis les étapes |
| `legislative_stage.py` | une phase de la navette (lecture, CMP, promulgation) | dates et décision résumées |
| `debate.py` | une séance | contient ses points |
| `debate_point.py` | un point d'ordre du jour | **le niveau « sujet »** |
| `intervention.py` | une prise de parole | |
| `amendment.py` | un amendement | |
| `assembly_vote.py` | un scrutin | + `Voter`, `NominalVoteCount` |
| `agenda_item.py` | une séance prévue | `is_ready_to_scrape` déclenche la collecte |

### Les docstrings sont la spécification de scraping

Chaque entité s'ouvre sur un bloc qui donne l'URL exacte du fichier source et la correspondance champ par champ :

```
XML field mapping (inside acteur/PA{id}.xml):
    deputy_uid    → acteur/uid
    uid           → mandat/uid
    mandate_start → mandat/dateDebut
```

**Lis-les avant d'écrire un adaptateur.** C'est le seul endroit où le format de la source est documenté, et ça a été écrit en regardant de vrais fichiers.

### Trois choses à savoir avant de toucher aux entités

**1. `model_config` est le premier membre de chaque classe.**

```python
class Deputy(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,   # accepte l'alias de la source ET le nom python
        from_attributes=True,    # peut se construire depuis une ligne SQL
    )

    uid: NotBlankStr
```

`populate_by_name=True` est ce qui permet d'écrire `AgendaItem(date_debut=…)` avec le nom français de la source **et** `item.start_date` avec le nom anglais dans le code.

**2. Les champs qui peuvent manquer sont optionnels — pour de vrai.**

`Mandate.department_name` a été passé de `NotBlankStr` à `str | None` en J1. Raison : les députés des Français établis hors de France n'ont pas de département, et certains organes ont un `<libelleAbrege/>` vide. Avec un champ obligatoire, ces enregistrements lèvent une `ValidationError`.

Le principe : **la validation stricte protège des données incohérentes, elle ne doit pas rejeter des données réelles mais inhabituelles.** Quand la réalité contredit le modèle, c'est le modèle qui a tort.

**3. Les enums sont des `StrEnum`, avec les libellés de la source.**

```python
class VoteResult(StrEnum):
    ADOPTED = "adopté"
    REJECTED = "rejeté"
```

Les valeurs sont **en français**, parce que c'est ce que l'Assemblée publie et que `raw` doit rester fidèle. Le schéma d'affichage, lui, attend `'adopted'` / `'rejected'`.

> ⚠️ **Ne jamais mettre un enum du domaine dans une ligne destinée à `public`.** Postgres répondra `invalid input value for enum law_status`. La traduction passe par une table de correspondance explicite, côté projection — voir le document 03.

---

## `ports/` — les prises murales

Un port est une classe abstraite (`ABC`) écrite avec les mots du métier. Elle dit ce qu'on peut obtenir ; elle ne dit jamais comment.

```
ports/
├── sources/        je LIS chez l'Assemblée nationale
├── repositories/   j'ÉCRIS dans le schéma raw
├── projections/    je TRANSFORME raw → public
└── storage.py      je dépose un fichier brut dans S3
```

### Pourquoi trois familles plutôt qu'une

Parce que le suffixe permet de savoir, **sans ouvrir le fichier**, dans quel sens vont les données et à quoi s'attendre :

- une **source** peut être lente, tomber en panne, changer de format sans prévenir ;
- un **dépôt** écrit dans un schéma qu'on possède, de façon idempotente, sans jamais supprimer ;
- une **projection** ne touche à aucun réseau et peut donc être relancée à volonté.

L'ancien fichier `ports/deputy_repository.py` déclarait `fetch_all` et `fetch_by_uid`. Il s'appelait *repository* mais ne persistait rien : c'était une source. Il est devenu `ports/sources/deputy_source.py`. Un nom qui ment coûte plus cher qu'un renommage.

### Ce qu'un port promet, au-delà de sa signature

Un port ne se limite pas à ses noms de méthodes. Il porte aussi des garanties, écrites dans ses docstrings, sur lesquelles les cas d'usage s'appuient :

- `DeputyRepository.save` est **idempotent** — deux appels identiques donnent une seule ligne ;
- il **n'ouvre pas de transaction** — c'est le cas d'usage qui en ouvre une par entité ;
- `LawRepository.save_article` **n'écrase jamais un texte** — il crée une version.

Quand tu écris un adaptateur, ces phrases sont ton cahier des charges.

### Une méthode d'ABC que personne n'implémente est un mensonge

`fetch_career` a été supprimée en J1. Elle était déclarée abstraite, aucun adaptateur ne l'implémentait, aucun appelant ne s'en servait. Un port doit décrire ce que l'application sait faire aujourd'hui — pas ce qu'on imagine faire un jour.

Même logique pour les fichiers vides : les sept ports de 0 octet ont été supprimés. **Un fichier vide est pire qu'un fichier absent** : il laisse croire qu'un contrat existe.

---

## `shared/` — le vocabulaire commun

### `validators.py`

```python
NotBlankStr = Annotated[str, BeforeValidator(_not_blank)]   # nettoie et refuse le vide
Legislature = Annotated[int, Field(ge=1)]                   # un entier positif
```

`BeforeValidator` s'exécute **avant** la validation de type. C'est ce qui permet à `"  PA1592  "` de devenir `"PA1592"` plutôt que d'être accepté avec ses espaces — dans un XML, les espaces autour d'une valeur sont la norme.

### `results.py`

`SyncReport` est le compte-rendu d'une exécution, et c'est **le même objet** que renvoient la route HTTP et la commande CLI.

```python
report.processed   # vu dans la source
report.created     # inséré
report.updated     # déjà là, mis à jour
report.skipped     # ignoré volontairement (dry-run, type sans destination)
report.failed      # erreur, journalisée, run poursuivi
```

Deux détails valent une explication.

**`ok` tolère 20 % d'échecs, mais rejette un run vide.** Un run qui ne traite rien n'est pas un succès : c'est le symptôme d'une source vide ou d'un filtre trop strict. Et au-delà de 20 % d'échecs, l'hypothèse la plus probable est que l'Assemblée a changé son format. Sans ce seuil, un parseur cassé produit des runs verts pendant des semaines.

**La liste d'erreurs est bornée à 20 uid.** Une réponse HTTP contenant 600 identifiants n'aide personne ; les traces complètes sont dans les logs. Cette liste sert à rejouer quelques cas à la main.

Ces objets sont des `dataclass` et non des modèles Pydantic : aucune donnée extérieure n'entre ici, il n'y a rien à valider.

---

## Ce à quoi le domaine sera relié plus tard

Aujourd'hui, `domain/` est presque seul : seuls les tests l'utilisent. Voilà qui s'y branchera, et quand.

| Ce qui arrive | Quand | Se branche sur |
|---|---|---|
| `AnDeputyAdapter` | J3 | implémente `DeputySource` |
| `SqlRawDeputyRepository` | J3 | implémente `DeputyRepository` |
| `CollectDeputies` | J3 | orchestre les deux, renvoie un `SyncReport` |
| `SqlDeputyProjection` | J3 | implémente `DeputyProjection` |
| Routes FastAPI + CLI | J3 | déclenchent les cas d'usage |
| `AnLawAdapter` | J4 | `LawSource`, `LawRepository` |
| `AnDebateAdapter` | J5 | `DebateSource`, `DebateRepository` |

Remarque le sens : **rien de tout ça n'obligera à modifier le domaine.** Si l'un de ces travaux demande de changer une entité ou un port, c'est le signal qu'on a mal compris quelque chose — et ça vaut la peine de s'arrêter pour en parler.

---

## Vérifier son travail

```bash
uv run ruff check .        # style et imports
uv run pytest -q           # 13 tests, dont les 3 garde-fous d'architecture
```

Les trois tests de `tests/unit/test_architecture.py` sont ceux à surveiller : ils échouent dès qu'un fichier du domaine importe une brique technique.

## Pour aller plus loin

- [Pydantic v2 — les modèles](https://docs.pydantic.dev/latest/concepts/models/)
- [Annotated et les validateurs](https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators)
- [`abc` — les classes abstraites en Python](https://docs.python.org/3/library/abc.html)
- [`StrEnum`](https://docs.python.org/3/library/enum.html#enum.StrEnum)

**Précédent : [00 — L'architecture](./00-architecture.md).** Suite : `02-config-logs.md` (J2).
