# 00 — L'architecture, en une page

## Le problème qu'on essaie de résoudre

Ce dépôt fait une seule chose : **récupérer les données ouvertes de l'Assemblée nationale et les mettre en base**. Ça a l'air simple, et ça ne l'est pas, pour deux raisons.

1. **La source change sans prévenir.** Les fichiers de l'Assemblée sont du XML et du JSON dont le format bouge d'une législature à l'autre, parfois d'un fichier à l'autre. Le compte rendu de séance appelle la date `dateSeance` dans un fichier et `DateSeance` dans le suivant.
2. **La base ne nous appartient pas entièrement.** Le schéma d'affichage est celui d'`isos-api`, conçu pour le front, pas pour nous.

Toute l'architecture découle de ces deux phrases. Elle sert à contenir l'instabilité dans des endroits précis, pour que le reste du code n'ait pas à s'en soucier.

---

## Trois schémas, trois propriétaires

C'est la décision la plus structurante du projet. On sépare **ce qu'on collecte**, **ce qu'on affiche**, et **ce que le modèle génère**.

```
┌──────────────────────────────────────────────────────────────┐
│  Assemblée nationale  (XML, JSON, ZIP)                       │
└───────────────────────────┬──────────────────────────────────┘
                            │  collecte
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  schéma  raw      ← isos-data-worker (nous)                  │
│  Les FAITS, fidèles à la source. Clé primaire = uid de l'AN. │
│  On n'y supprime jamais rien.                                │
└───────────────────────────┬──────────────────────────────────┘
                            │  projection (aucun réseau)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  schéma  public   ← isos-api                                 │
│  Ce que le front affiche. Slugs, identifiants entiers,       │
│  libellés en anglais, contenus éditorialisés.                │
└───────────────────────────┬──────────────────────────────────┘
                            │  lecture
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  schéma  rag      ← isos-llm-engine                          │
│  Résumés, découpages, vecteurs. Généré par un modèle,        │
│  donc jamais un fait.                                        │
└──────────────────────────────────────────────────────────────┘
```

Ce n'est pas une invention maison : le projet fait déjà exactement ça pour le CMS. `isos-api/docs/database_security.md` définit le rôle `isos_directus` comme *« `cms` schema only. No access to `public` at all »*. On applique la même règle à l'ingestion.

### Ce que cette séparation nous achète, concrètement

**On ne confond plus un fait et une phrase écrite par un modèle.** Si un résumé généré est faux, il est faux dans `rag`. Ce que l'Assemblée a réellement publié reste intact dans `raw`, et on peut le prouver.

**Rejouer une correspondance ne coûte plus un appel réseau.** C'est le bénéfice qu'on ressent tous les jours. Un mauvais libellé, un slug mal construit ? On relance `project-deputies`, wifi coupé, deux secondes. Sans le schéma `raw`, il faudrait re-télécharger 600 fichiers pour corriger une faute de frappe.

**On peut créer nos propres tables sans rien négocier.** Le worker est propriétaire de `raw` (`CREATE SCHEMA raw AUTHORIZATION isos_ingestion`), donc il a son propre Alembic, dans son propre dépôt. Une migration dans `isos-api` demande de coordonner deux personnes et deux dépôts ; dans `raw`, c'est une commande.

**Deux entités retrouvent un toit.** `DebatePoint` et `Intervention` n'avaient littéralement aucune table où atterrir : le schéma d'affichage aplatit une séance en une seule ligne. Or c'est précisément ce découpage par sujet — « questions au gouvernement », « discussion du projet de loi X » — qu'il faut pour résumer une séance sujet par sujet.

### La règle d'or de `raw`

> **On n'y supprime jamais rien, et on n'y écrase jamais un texte.**

Une donnée qui disparaît de l'export de l'Assemblée garde sa ligne ; c'est sa colonne `last_seen_at` qui cesse d'avancer. Un article de loi dont le texte change ne remplace pas l'ancien : une nouvelle version est créée, et la précédente est marquée non courante.

Ce n'est pas une coquetterie. Le moteur de recherche sémantique découpe les textes et indexe chaque morceau. Si on modifie une ligne en place, un morceau déjà indexé renvoie un texte qui n'a jamais été celui qu'on a indexé — et personne ne s'en aperçoit.

---

## Les quatre couches du code

Dans le dépôt, `src/` est découpé en quatre anneaux. Une seule règle les gouverne.

```
        interfaces/          « comment on me déclenche »
             │                 API HTTP, ligne de commande
             ▼
        application/         « ce que le produit sait faire »
             │                 collecter les députés, projeter les lois
             ▼
          domain/            « de quoi on parle »
             ▲                 entités, ports, règles métier
             │
      infrastructure/        « comment on s'y prend vraiment »
                               httpx, lxml, boto3, SQLAlchemy
```

**Les flèches vont toujours vers le centre.** `domain/` ne connaît personne. `application/` ne connaît que `domain/`. `infrastructure/` et `interfaces/` connaissent tout le reste — ce sont les couches qu'on jette et qu'on réécrit.

Cette règle n'est pas déclarative : elle est **testée**. Voir `tests/unit/test_architecture.py`, qui lit l'arbre syntaxique de chaque fichier du domaine et échoue si l'un d'eux importe `httpx`, `sqlalchemy`, ou `src.infrastructure`. Un test qui casse ici veut dire qu'un fichier est au mauvais endroit — ce n'est pas le test qu'il faut corriger.

### Pourquoi ces noms-là

| Dossier | Le nom veut dire | Ce qu'on y met |
|---|---|---|
| `domain/entities/` | les choses dont parle le métier | `Deputy`, `Law`, `Debate` — des données validées, sans comportement technique |
| `domain/ports/` | les prises murales | des classes abstraites : « je sais lire des députés », sans dire comment |
| `domain/shared/` | le vocabulaire commun | validateurs, compte-rendus d'exécution |
| `application/use_cases/` | un fichier = un verbe | `collect_deputies`, `project_laws` — ce qu'on peut demander au produit |
| `infrastructure/` | les fiches qu'on branche | les implémentations concrètes des ports |
| `interfaces/` | les portes d'entrée | l'API et le CLI, qui déclenchent les mêmes cas d'usage |

Le point important sur `interfaces/` : l'API HTTP et la ligne de commande sont **au même niveau**, côte à côte. Aucune des deux n'est « la vraie ». Elles appellent le même cas d'usage et obtiennent le même compte-rendu. C'est ce qui permet de lancer une collecte depuis un Job Kubernetes sans serveur HTTP, et depuis une route quand on veut la déclencher à la main.

---

## Port et adaptateur : la seule métaphore à retenir

**Un port est une prise murale.** Une classe abstraite dans `domain/`, écrite avec les mots du métier. Elle dit *ce qu'on peut obtenir*, jamais *comment*.

```python
class DeputySource(ABC):
    @abstractmethod
    async def fetch_all(self, legislature, limit=None) -> list[Deputy]: ...
```

**Un adaptateur est la fiche qu'on branche dedans.** Une classe concrète dans `infrastructure/`, qui sait télécharger un ZIP, gérer un namespace XML et retenter sur un timeout.

```python
class AnDeputyAdapter(DeputySource):
    async def fetch_all(self, legislature, limit=None) -> list[Deputy]:
        ...  # httpx, zipfile, lxml
```

Le jour où l'Assemblée change son format, **un seul fichier change** : l'adaptateur. Les entités, les cas d'usage et leurs tests ne bougent pas — ils dépendent du port, qu'un faux peut remplacer en trois lignes dans un test.

### Le suffixe dit la direction

Trois familles de ports, et le nom suffit à savoir où on est :

| Famille | Sens | Exemple |
|---|---|---|
| `ports/sources/` | je **lis** chez quelqu'un d'autre | `DeputySource` — l'Assemblée nationale |
| `ports/repositories/` | j'**écris** chez moi | `DeputyRepository` — le schéma `raw` |
| `ports/projections/` | je **transforme** raw → public | `DeputyProjection` |

C'est pour ça que l'ancien fichier `ports/deputy_repository.py`, qui déclarait `fetch_all` et `fetch_by_uid`, a été renommé en `ports/sources/deputy_source.py`. Il ne persistait rien : c'était une source. Garder le mot *repository* pour ce qui persiste évite qu'un relecteur se trompe sur ce qu'il lit.

---

## Les deux moitiés du pipeline

Chaque jeu de données donne **deux** cas d'usage, et il faut bien voir qu'ils ne font pas le même métier.

|  | `collect_*` | `project_*` |
|---|---|---|
| Va chercher | l'Assemblée nationale | le schéma `raw` |
| Écrit dans | `raw` | `public` |
| Réseau | oui, lent, peut échouer | **aucun** |
| Clé | l'uid de l'AN | un entier, l'uid part dans `external_id` |
| Libellés | tels quels, en français | traduits vers les enums Postgres |
| Slugs | aucun | générés, obligatoires et uniques |
| Champs sans destination | conservés | perdus, et c'est assumé |

Toute la complexité d'adaptation — slugs, traduction d'enums, résolution de clés étrangères, troncature d'un titre trop long — se concentre dans la moitié droite, **celle qui ne dépend d'aucun réseau et qu'on peut donc relancer autant de fois qu'on veut**. C'est le cœur du bénéfice.

---

## Pour aller plus loin

- [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) — l'article d'origine, court, avec le schéma des anneaux concentriques.
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) — Alistair Cockburn, l'inventeur de la métaphore ports/adaptateurs.
- [Architecture médaillon](https://www.databricks.com/glossary/medallion-architecture) — le nom industriel de notre découpage brut → affiné → servi.
- [12-factor : la configuration](https://12factor.net/config) — pourquoi la config vit dans l'environnement.

**Suite : [01 — Le domaine](./01-domain.md).**
