#!/bin/sh
set -e

# Apply the raw-schema migrations before serving, so a fresh database needs
# no manual `make migrate`. Idempotent: a no-op when already at head.
uv run alembic upgrade head

exec "$@"
