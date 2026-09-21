# isos-data-worker — everyday commands. `make` alone lists them.
#
#   make sync DEBATES=5     the 5 latest sittings and everything they touch (deputies: all)
#   make sync               the whole legislature (amendments: 340 MB, ~15 min)
#   make collect DS=laws    one dataset, Assemblée → raw       make project DS=laws   raw → public
#   make refresh            re-download the archives into S3

SHELL := /bin/bash
CLI   := uv run python -m src.interfaces.cli
LEG   ?= 17
DS    ?= deputies
DEBATES ?=

.DEFAULT_GOAL := help

help: ## list the commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F ':.*?## ' '{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── run ───────────────────────────────────────────────────────────────────────

sync: ## collect + project everything; DEBATES=N scopes to the N latest sittings
	$(CLI) --legislature $(LEG) sync-all $(if $(DEBATES),--debates $(DEBATES))

collect: ## Assemblée → raw for one dataset (DS=deputies|laws|agenda|debates|amendments|ballots|law-texts)
	$(CLI) --legislature $(LEG) collect-$(DS) $(ARGS)

project: ## raw → public for one dataset (DS=…), no network
	$(CLI) --legislature $(LEG) project-$(DS)

refresh: ## re-download the archives into S3 (database untouched); DS="laws agenda" to pick
	$(CLI) --legislature $(LEG) refresh $(if $(filter-out deputies,$(DS)),$(DS),)

api: ## serve the HTTP API on :8001
	uv run python -m src.main

# ── infrastructure ────────────────────────────────────────────────────────────

up: ## start Garage (S3) and its web UI
	docker compose up -d garage garage-webui && ./docker/garage/bootstrap.sh

down: ## stop the containers
	docker compose down

migrate: ## apply the raw-schema migrations
	uv run alembic upgrade head

migration: ## write a migration from the tables (MSG="…")
	uv run alembic revision --autogenerate -m "$(MSG)"

# ── quality ───────────────────────────────────────────────────────────────────

install: ## install dependencies
	uv sync

test: ## run the tests
	uv run pytest -q

lint: ## ruff check + format check
	uv run ruff check . && uv run ruff format --check .

fmt: ## ruff format
	uv run ruff format . && uv run ruff check --fix .

check: lint test ## everything CI runs

.PHONY: help sync collect project refresh api up down migrate migration install test lint fmt check
