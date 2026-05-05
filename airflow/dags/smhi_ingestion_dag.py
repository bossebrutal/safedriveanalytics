"""
Airflow DAG: SMHI väderdata ingestion.

Kör varje timme och hämtar senaste väderobservationer från SMHI.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "safedriveanalytics",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="smhi_weather_ingestion",
    description="Hämtar väderobservationer från SMHI Open Data API varje timme",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["ingestion", "smhi", "weather"],
) as dag:

    def ingest():
        from ingestion.smhi.ingest_smhi import run_ingestion

        return run_ingestion()

    ingest_weather = PythonOperator(
        task_id="ingest_smhi_weather",
        python_callable=ingest,
        doc_md="Hämtar temperatur, nederbörd, vind och snödjup från SMHI:s API.",
    )
