#!/bin/bash
# Skapar en separat databas för MLflow tracking server.
# Körs automatiskt av postgres-containern vid första uppstarten.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE mlflow'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec
    GRANT ALL PRIVILEGES ON DATABASE mlflow TO ${POSTGRES_USER};
EOSQL
