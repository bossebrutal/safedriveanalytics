"""
Airflow DAG: Trafikverket trafikdata ingestion.

Kör var 15:e minut och hämtar senaste trafikflöde och incidenter.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "safedriveanalytics",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
}

with DAG(
    dag_id="trafikverket_traffic_ingestion",
    description="Hämtar trafikflöde och incidenter från Trafikverkets API var 15:e minut",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="*/15 * * * *",
    catchup=False,
    tags=["ingestion", "trafikverket", "traffic"],
) as dag:

    def ingest_flow():
        from ingestion.trafikverket.ingest_trafikverket import run_ingestion

        return run_ingestion()

    ingest_traffic = PythonOperator(
        task_id="ingest_trafikverket_traffic",
        python_callable=ingest_flow,
        doc_md="Hämtar trafikflödesmätningar och aktiva incidenter från Trafikverkets API.",
    )
