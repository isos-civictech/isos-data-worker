# isos-data-worker

Collects the [Assemblée nationale open data](https://data.assemblee-nationale.fr), keeps the
archives in S3, stores every fact in the `raw` Postgres schema, and projects what the product
displays into the `public` schema read by `isos-api`.

```text
Assemblée nationale ──collect──▶ S3 (Garage) ──▶ schema raw ──project──▶ schema public ──▶ isos-api
                                                     └────────────────────────────────────▶ isos-llm-engine
```

The full documentation (architecture, datasets, operations) is in
[isos-doc › Scraper](../isos-doc/content/docs/scraper). This file is the quick start.

## Quick start

Requirements: Docker, Python 3.12, [uv](https://docs.astral.sh/uv/), and `isos-api` cloned
next to this repo (it owns Postgres and the `isos_ingestion` role).

```bash
# 1. Postgres, from isos-api
docker network create isos-network                       # once
(cd ../isos-api && docker compose up -d db)              # then its `alembic upgrade head`

# 2. Configuration
cp .env.example .env        # DATABASE_URL password = ISOS_INGESTION_DB_PASSWORD from isos-api's .env

# 3. S3 (Garage) — bootstraps the bucket and prints an access key if .env has none
make up

# 4. Install, migrate, check
make install
make migrate
make check
```

## Everyday commands

```bash
make sync DEBATES=5        # every deputy, then the 5 latest sittings and what they touch
make sync                  # the whole legislature (~20 min the first time)
make collect DS=laws       # one dataset, Assemblée → raw   (S3 copy used when present)
make project DS=laws       # one dataset, raw → public      (no network)
make refresh               # re-download the archives into S3
make api                   # HTTP API on :8001 — /docs for OpenAPI, / for the guide
make                       # list everything
```

`DS` ∈ `deputies laws agenda debates amendments ballots law-texts`.
Any `make collect` accepts `ARGS="--limit 5 --dry-run"`, `--uid …`, `--dossier DLR…`,
`--since/--until YYYY-MM-DD`, `--refresh`.

The HTTP API exposes the same pipeline: `POST /sync/all?debates=5`, `POST /sync/{dataset}`,
`POST /collect/{dataset}`, `POST /project/{dataset}`, `POST /refresh`, plus read routes
(`/agenda/today`, `/laws/{uid}`, `/laws/{uid}/articles/{ref}`, `/deputies/{uid}/votes`, `/jobs`).

## Layout

```text
src/
├── domain/          entities (Pydantic, docstring = field mapping) + ports (ABCs)
├── application/     use cases: collect_*, project_*, sync_all, refresh_archives
├── infrastructure/  adapters/ (parsers), persistence/{raw,serving}/, storage/, http/
├── interfaces/      cli.py, api/, dispatch.py
└── composition.py   wires everything (the only place importing both application and infrastructure)
migrations/          Alembic for the raw schema (autogenerate from persistence/raw/tables.py)
tests/               unit (pure), adapters (real trimmed fixtures), application (fakes), interfaces
```

Rules that keep it maintainable: `raw` is faithful and never deleted, `public` is only what
the front shows, every projected row carries the AN uid as `external_id`, every run is
idempotent (run it twice: `created: 0`). Details and the "add a dataset" checklist:
[isos-doc › Scraper › Architecture](../isos-doc/content/docs/scraper/architecture.mdx).

## Related repositories

`isos-api` (public schema, FastAPI) · `isos-web` (Next.js) · `isos-llm-engine` (rag schema) ·
`isos-ops` (K3S, ArgoCD) · `isos-doc` (this documentation).
