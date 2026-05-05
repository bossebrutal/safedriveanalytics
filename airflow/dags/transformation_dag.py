"""
Airflow DAG: Dataomvandling och feature engineering.

Körs efter att ingestion-DAGarna har kört och förbereder data
för ML-modellträning.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

default_args = {
    "owner": "safedriveanalytics",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="data_transformation",
    description="Transformerar och sammanfogar väder- och trafikdata för ML",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["transformation", "ml"],
) as dag:

    wait_for_weather = ExternalTaskSensor(
        task_id="wait_for_smhi_ingestion",
        external_dag_id="smhi_weather_ingestion",
        external_task_id="ingest_smhi_weather",
        timeout=600,
        poke_interval=30,
        mode="reschedule",
    )

    def transform():
        from transformation.transform_and_merge import run_transformation

        return run_transformation()

    def train():
        from ml_model.train import run_training

        return run_training()

    run_transform = PythonOperator(
        task_id="transform_and_merge",
        python_callable=transform,
        doc_md=(
            "Sammanfogar väder- och trafikdata baserat på geografisk "
            "och tidsmässig proximity. Skapar features för ML-modellen."
        ),
    )

    run_train = PythonOperator(
        task_id="train_ml_model",
        python_callable=train,
        doc_md="Tränar GradientBoosting-modellen på senaste ml_features och sparar model.joblib.",
    )

    wait_for_weather >> run_transform >> run_train
