#!/usr/bin/env bash
# Garage bootstrap — runs on the HOST and drives the container's `garage` CLI.
# The dxflrs/garage image is distroless (no shell), so this cannot run inside it.
#
#   ./docker/garage/bootstrap.sh
#
# Idempotent: layout, key, bucket and grant are only created when missing.
set -euo pipefail

cd "$(dirname "$0")/../.."
set -a; source .env; set +a

: "${S3_ACCESS_KEY:?set S3_ACCESS_KEY in .env}"
: "${S3_SECRET_KEY:?set S3_SECRET_KEY in .env}"
: "${S3_BUCKET_RAW:=isos-raw}"

garage() { docker compose exec -T garage /garage -c /etc/garage/garage.toml "$@"; }

echo "waiting for garage..."
until garage status >/dev/null 2>&1; do sleep 1; done

NODE_ID=$(garage status | awk '/NO ROLE ASSIGNED/ {print $1; exit}' || true)
if [[ -n "${NODE_ID}" ]]; then
    echo "assigning layout to ${NODE_ID}"
    garage layout assign -z dc1 -c 1G "${NODE_ID}"
    garage layout apply --version 1
else
    echo "layout already assigned"
fi

if garage key info "${S3_ACCESS_KEY}" >/dev/null 2>&1; then
    echo "key already present"
elif garage key import --yes -n isos-worker "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" 2>/dev/null; then
    echo "key imported from .env"
else
    echo "import refused — generating a key instead; copy it into .env and re-run:"
    garage key create isos-worker
    garage key info --show-secret isos-worker
    exit 1
fi

if garage bucket info "${S3_BUCKET_RAW}" >/dev/null 2>&1; then
    echo "bucket already exists"
else
    echo "creating bucket ${S3_BUCKET_RAW}"
    garage bucket create "${S3_BUCKET_RAW}"
fi

garage bucket allow --read --write --owner "${S3_BUCKET_RAW}" --key "${S3_ACCESS_KEY}"
echo "ready"
garage bucket info "${S3_BUCKET_RAW}"
