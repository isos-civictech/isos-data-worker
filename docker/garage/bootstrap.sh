#!/bin/sh
# Garage bootstrap — one-shot, idempotent, safe to re-run.
#
# A fresh Garage node knows nothing: no storage layout, no access key, no
# bucket. None of it can be baked into the image, because the node id only
# exists once the daemon is running. Hence a separate container that runs these
# four steps and exits.
set -eu

: "${S3_ACCESS_KEY:?set S3_ACCESS_KEY in .env}"
: "${S3_SECRET_KEY:?set S3_SECRET_KEY in .env}"
: "${S3_BUCKET_RAW:=isos-raw}"

echo "garage-bootstrap: waiting for the daemon..."
until /garage status >/dev/null 2>&1; do
    sleep 1
done

# 1. Storage layout. Without it every write fails with "no storage nodes".
NODE_ID=$(/garage status | awk '/NO ROLE ASSIGNED/ {print $1; exit}')
if [ -n "${NODE_ID:-}" ]; then
    echo "garage-bootstrap: assigning layout to ${NODE_ID}"
    /garage layout assign -z dc1 -c 1G "${NODE_ID}"
    /garage layout apply --version 1
else
    echo "garage-bootstrap: layout already assigned"
fi

# 2. Access key.
#
# `key import` forces the values chosen in .env instead of letting Garage
# generate random ones — that is what allows the worker to be configured before
# Garage has ever started. If Garage rejects the format, fall back to letting it
# generate a pair and print it loudly, so it can be pasted into .env.
if /garage key info "${S3_ACCESS_KEY}" >/dev/null 2>&1; then
    echo "garage-bootstrap: key already present"
elif /garage key import --yes -n isos-worker "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" 2>/dev/null; then
    echo "garage-bootstrap: key imported from .env"
else
    echo "garage-bootstrap: WARNING — import refused, generating a key instead."
    echo "garage-bootstrap: copy the values below into .env, then re-run."
    /garage key create isos-worker
    /garage key info --show-secret isos-worker
    exit 1
fi

# 3. Bucket.
if /garage bucket info "${S3_BUCKET_RAW}" >/dev/null 2>&1; then
    echo "garage-bootstrap: bucket already exists"
else
    echo "garage-bootstrap: creating bucket ${S3_BUCKET_RAW}"
    /garage bucket create "${S3_BUCKET_RAW}"
fi

# 4. Permissions. A bucket with no grant is readable by nobody.
/garage bucket allow --read --write --owner "${S3_BUCKET_RAW}" --key "${S3_ACCESS_KEY}"

echo "garage-bootstrap: ready"
/garage bucket info "${S3_BUCKET_RAW}"
