"""
Airflow DAG: ML-modellträning (daglig).

Tränar GradientBoosting-modellen på de senaste ml_features och
loggar till MLflow. Ny modell promotas till "champion" om R² är bättre
än nuvarande champion (champion/challenger-mönster).

Körs separat från transformation_dag för att:
- Inte träna i onödan varje timme (dyrt, onödigt)
- Kunna triggas manuellt vid behov
- Ge en tydlig separation mellan datapipeline och ML-pipeline
"""

from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator

from airflow import DAG

default_args = {
    "owner": "safedriveanalytics",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}

with DAG(
    dag_id="ml_model_training",
    description="Daglig ML-modellträning med champion/challenger-logik via MLflow",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["ml", "training"],
) as dag:

    def train():
        from ml_model.train import run_training

        result = run_training()
        if result["status"] == "skipped":
            raise ValueError(f"För lite träningsdata: {result['rows']} rader (minst 100 krävs)")
        return result

    run_train = PythonOperator(
        task_id="train_ml_model",
        python_callable=train,
        doc_md=(
            "Tränar GradientBoosting-modellen på senaste ml_features. "
            "Ny modell promotas till 'champion' i MLflow Model Registry om R² förbättras."
        ),
    )
