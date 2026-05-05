#!/usr/bin/env bash
# run_pipeline.sh – Kör hela datapipelinen: ingest → transform → train
# Användning:
#   ./run_pipeline.sh          # kör en gång
#   ./run_pipeline.sh --loop   # kör i loop var 15:e minut

set -euo pipefail

PYTHON=/home/patrikwinkler/anaconda3/envs/safedriveanalytics/bin/python
DIR="$(cd "$(dirname "$0")" && pwd)"

export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-safedriveanalytics}"
export POSTGRES_USER="${POSTGRES_USER:-sda_user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change_me_in_production}"

run_once() {
    echo "[$(date '+%H:%M:%S')] === Startar pipeline ==="

    echo "[$(date '+%H:%M:%S')] 1/3 Hämtar SMHI-väderdata..."
    "$PYTHON" -m ingestion.smhi.ingest_smhi 2>&1 | grep -E "INFO:__main__|ERROR|Traceback"

    echo "[$(date '+%H:%M:%S')] 2/3 Hämtar Trafikverket-data..."
    "$PYTHON" -m ingestion.trafikverket.ingest_trafikverket 2>&1 | grep -E "INFO:__main__|ERROR|Traceback"

    echo "[$(date '+%H:%M:%S')] 3/3 Transformerar och uppdaterar ml_features..."
    "$PYTHON" -c "
import logging, os
logging.basicConfig(level=logging.WARNING)
from transformation.transform_and_merge import run_transformation
n = run_transformation()
print(f'  → {n} nya feature-rader skapade')
"

    # Hämta antal rader i ml_features
    N=$("$PYTHON" -c "
import os, psycopg2
conn = psycopg2.connect(host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'],
    dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'])
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM ml_features WHERE temperature_c IS NOT NULL')
print(cur.fetchone()[0])
conn.close()
")
    echo "[$(date '+%H:%M:%S')]    ml_features totalt: $N rader"

    if [ "$N" -ge 100 ]; then
        echo "[$(date '+%H:%M:%S')] 4/4 Tränar ML-modellen ($N rader)..."
        "$PYTHON" -m ml_model.train 2>&1 | grep -E "Träning klar|MAE|ERROR|Traceback"
    else
        echo "[$(date '+%H:%M:%S')] 4/4 Hoppar träning – behöver minst 100 rader (har $N)"
    fi

    echo "[$(date '+%H:%M:%S')] === Pipeline klar ==="
}

if [ "${1:-}" = "--loop" ]; then
    INTERVAL="${2:-900}"  # sekunder (standard: 15 min)
    echo "Kör pipeline var ${INTERVAL}s. Avbryt med CTRL+C."
    while true; do
        run_once
        echo "Väntar ${INTERVAL}s..."
        sleep "$INTERVAL"
    done
else
    run_once
fi
