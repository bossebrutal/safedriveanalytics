#!/bin/sh
set -e

exec mlflow server \
  --host 0.0.0.0 \
  --port "${PORT:-5000}" \
  --backend-store-uri "postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/mlflow" \
  --artifacts-destination "gs://${MLFLOW_ARTIFACT_BUCKET}" \
  --serve-artifacts \
  --allowed-hosts '*'
