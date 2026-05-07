#!/bin/sh
set -e

# URL-encode password to handle special characters in the connection URI
ENCODED_PASSWORD=$(python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "${POSTGRES_PASSWORD}")

exec mlflow server \
  --host 0.0.0.0 \
  --port "${PORT:-5000}" \
  --backend-store-uri "postgresql+psycopg2://${POSTGRES_USER}:${ENCODED_PASSWORD}@${POSTGRES_HOST}:5432/mlflow" \
  --artifacts-destination "gs://${MLFLOW_ARTIFACT_BUCKET}" \
  --serve-artifacts \
  --allowed-hosts '*'
