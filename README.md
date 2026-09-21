# isos-data-worker

Collecte les données ouvertes de l'[Assemblée nationale](https://data.assemblee-nationale.fr) et les
écrit dans le schéma `raw` de la base ISOS, puis les projette vers le schéma `public` lu par `isos-api`.

```text
Assemblée nationale  (XML, JSON, ZIP)
        │  collecte      réseau, lent — les fichiers bruts sont archivés dans Garage (S3)
        ▼
  schéma raw         les faits, tels que publiés — propriété de ce dépôt
        │  projection   SQL seul, aucun réseau
        ▼
  schéma public      ce que le front affiche — propriété d'isos-api
```

Le service expose une API HTTP (port `8001`) et une ligne de commande ; les deux appellent exactement les
mêmes cas d'usage. Le raisonnement complet est dans [docs/00-architecture.md](docs/00-architecture.md).

## Prérequis

- Docker et Docker Compose
- Le dépôt `isos-api` cloné à côté (`../isos-api`) — c'est lui qui possède Postgres, le rôle
  `isos_ingestion` et le schéma `raw`
- Pour lancer sans Docker : Python 3.12 et [uv](https://docs.astral.sh/uv/)

## Démarrage rapide

### 1. Base de données (depuis isos-api)

Le worker n'a **pas** son propre Postgres : il écrit dans la même base qu'`isos-api`, avec le rôle
`isos_ingestion` (propriétaire de `raw`, écriture seule sur les tables de contenu de `public`, aucun
`DELETE`, aucun accès aux données utilisateurs).

```bash
docker network create isos-network        # une seule fois
cd ../isos-api && docker compose up -d db
```

### 2. Configuration

```bash
cp .env.example .env
```

| Variable | Rôle |
| --- | --- |
| `DATABASE_URL` | URL asyncpg vers Postgres. Le mot de passe est `ISOS_INGESTION_DB_PASSWORD` du `.env` d'isos-api. Hôte `db` depuis Docker, `localhost` depuis la machine. |
| `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Accès à Garage. **Obligatoires** : sans stockage des fichiers bruts, le worker refuse de démarrer une collecte. |
| `S3_BUCKET_RAW` | Bucket des archives brutes (`isos-raw`). |
| `AN_BASE_URL` / `AN_LEGISLATURE` | Source et législature par défaut (`17`). |
| `LOG_LEVEL` | `INFO` par défaut. |

Générez la paire de clés S3 (Garage impose le format `GK` + 24 hex / 64 hex) :

```bash
python -c "import secrets; print('GK'+secrets.token_hex(12)); print(secrets.token_hex(32))"
```

### 3. Garage (stockage objet)

```bash
docker compose up -d garage
docker compose run --rm garage-bootstrap    # layout + clé + bucket + droits ; idempotent
```

Le bootstrap importe la clé de votre `.env` dans Garage. S'il la refuse, il en génère une et l'affiche :
copiez-la dans `.env` et relancez.

### 4. Migrations du schéma `raw`

Le schéma lui-même est créé par l'initdb d'isos-api ; Alembic ne fait que le remplir.

```bash
uv sync
uv run alembic upgrade head
```

### 5. Lancer le worker

```bash
docker compose up --build scraper
```

Puis ouvrez <http://localhost:8001> — la page d'accueil liste tous les endpoints — ou
<http://localhost:8001/docs> pour l'OpenAPI interactif.

## Utilisation

### Ligne de commande

C'est l'entrée utilisée par les Jobs Kubernetes. Code de sortie : `0` si la collecte est acceptable,
`1` sinon — un Job échoue visiblement au lieu de réussir sur une base vide.

```bash
uv run python -m src.interfaces.cli collect-deputies --limit 5 --dry-run   # récupère et parse, n'écrit rien
uv run python -m src.interfaces.cli collect-deputies --legislature 17      # collecte complète
uv run python -m src.interfaces.cli collect-deputies --uid PA605036        # rejoue un seul député
```

### API HTTP

| Méthode | Route | Rôle |
| --- | --- | --- |
| `GET` | `/health` | Liveness — le processus répond, ne touche à rien d'autre |
| `GET` | `/health/db` | Readiness — `SELECT 1` sur Postgres, `503` sinon |
| `GET` | `/jobs?entity_type=&limit=` | Historique des collectes (`raw.ingestion_run`) |
| `GET` | `/jobs/summary` | Par entité : nombre de runs, dernier run, créés / échoués |
| `POST` | `/collect/deputies?legislature=&limit=&dry_run=` | Collecte tous les députés |
| `POST` | `/collect/deputies/{uid}` | Collecte un député par son uid AN |

```bash
curl -X POST "http://localhost:8001/collect/deputies?limit=5&dry_run=true"
curl http://localhost:8001/jobs/summary
```

## Développement

```bash
uv sync                    # dépendances + groupe dev
uv run pytest              # tests (asyncio_mode=auto, respx pour le HTTP)
uv run ruff check .        # lint : E, F, I, UP, B — ligne 100
uv run ruff format .
uv run python -m src.main  # API en local, sans Docker
```

`tests/unit/test_architecture.py` vérifie la règle de dépendance entre couches en lisant l'AST de
chaque fichier. S'il casse, c'est le fichier qui est au mauvais endroit, pas le test.

### Nouvelle migration

```bash
uv run alembic revision -m "description"    # écrite à la main, miroir de persistence/raw/tables.py
uv run alembic upgrade head
```

## Structure du code

```text
src/
├── domain/            entités, ports, règles métier — ne dépend de rien (sauf Pydantic)
│   ├── entities/      Deputy, Law, Debate, Amendment, Ballot, …
│   ├── ports/         sources (AN), repositories (raw), projections (public), storage (S3)
│   └── shared/        SyncReport, validateurs
├── application/       cas d'usage — collect_deputies
├── infrastructure/    adaptateurs concrets
│   ├── adapters/      parseurs XML/JSON de l'Assemblée (députés, lois, débats, amendements, scrutins, agenda)
│   ├── http/          client httpx avec retry (tenacity), lecture d'archives ZIP
│   ├── persistence/   engine SQLAlchemy async, tables et repositories du schéma raw
│   └── storage/       adaptateur Garage S3
├── interfaces/        API FastAPI (routes/) et CLI (cli.py)
├── composition.py     racine de composition — seul module qui relie infrastructure et application
├── config.py          Settings pydantic-settings (lit .env)
└── main.py            point d'entrée du conteneur (uvicorn)

migrations/            Alembic, schéma raw
docker/garage/         config Garage et script de bootstrap
docs/                  00-architecture, 01-domain
tests/                 unit/, adapters/, application/, interfaces/
```

### Règles du schéma `raw`

- Clé primaire = uid de l'Assemblée nationale.
- **On n'y supprime jamais rien** : une donnée absente d'un export garde sa ligne, seul `last_seen_at`
  cesse d'avancer.
- **On n'écrase jamais un texte** : une nouvelle version est créée, l'ancienne est marquée non courante.
- Chaque fichier source est archivé tel quel dans le bucket `isos-raw` avant parsing.

## Dépôts liés

| Dépôt | Rôle |
| --- | --- |
| `isos-api` | Postgres, rôles, schéma `public`, API du front |
| `isos-llm-engine` | Schéma `rag` : résumés, découpages, vecteurs |
| `isos-web` | Front |
| `isos-ops` | Déploiement Kubernetes (le Service cible le port `8001`) |

## Licence

Voir [LICENSE](LICENSE).
