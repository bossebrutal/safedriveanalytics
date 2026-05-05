"""
ML-modellträning: Prediktera trafikflöde utifrån väderförhållanden.

Använder MLflow för experiment-tracking och Model Registry.
Champion/challenger: ny modell deployas till Production endast om R² > nuvarande champion.
"""

import logging
import os
import sys

import mlflow
import mlflow.sklearn
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

load_dotenv()
logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "safedriveanalytics"
MODEL_NAME = "SafeDriveModel"

FEATURES = [
    "temperature_c",
    "precipitation_mm",
    "wind_speed_ms",
    "snow_depth_cm",
    "road_condition_code",
    "hour_of_day",
    "day_of_week",
    "month",
]
TARGET = "vehicle_flow"


def load_training_data() -> pd.DataFrame:
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    query = """
        SELECT
            vehicle_flow,
            temperature_c,
            COALESCE(precipitation_mm, 0) AS precipitation_mm,
            COALESCE(wind_speed_ms, 0)    AS wind_speed_ms,
            COALESCE(snow_depth_cm, 0)    AS snow_depth_cm,
            COALESCE(road_condition_code, 1) AS road_condition_code,
            EXTRACT(HOUR FROM measured_at)       AS hour_of_day,
            EXTRACT(DOW  FROM measured_at)       AS day_of_week,
            EXTRACT(MONTH FROM measured_at)      AS month
        FROM ml_features
        WHERE vehicle_flow IS NOT NULL
          AND temperature_c IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def train_model(df: pd.DataFrame) -> tuple[Pipeline, dict]:
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                GradientBoostingRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=4,
                    random_state=42,
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
        "training_rows": float(len(df)),
    }
    logger.info("Träning klar — MAE: %.1f fordon/h, R²: %.3f", metrics["mae"], metrics["r2"])
    return pipeline, metrics


def _promote_if_better(client: MlflowClient, new_version: str, new_r2: float) -> str:
    """Jämför challenger mot nuvarande champion. Returnerar 'promoted' eller 'staged'."""
    try:
        champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
        champion_run = client.get_run(champion.run_id)
        champion_r2 = float(champion_run.data.metrics.get("r2", -999))
        champion_version = champion.version
    except mlflow.exceptions.MlflowException:
        # Ingen champion finns ännu — promota direkt
        client.set_registered_model_alias(MODEL_NAME, "champion", new_version)
        logger.info("Ingen champion hittades – v%s satt som champion.", new_version)
        return "promoted"

    if new_r2 > champion_r2:
        # Challenger vinner — flytta champion-alias och arkivera gamla
        client.set_registered_model_alias(MODEL_NAME, "champion", new_version)
        client.delete_registered_model_alias(MODEL_NAME, "challenger") if _alias_exists(client, "challenger") else None
        logger.info(
            "Challenger v%s (R²=%.3f) slår champion v%s (R²=%.3f) → ny champion.",
            new_version, new_r2, champion_version, champion_r2,
        )
        return "promoted"
    else:
        # Champion håller ställningarna
        client.set_registered_model_alias(MODEL_NAME, "challenger", new_version)
        logger.info(
            "Challenger v%s (R²=%.3f) sämre än champion v%s (R²=%.3f) → staged som challenger.",
            new_version, new_r2, champion_version, champion_r2,
        )
        return "staged"


def _alias_exists(client: MlflowClient, alias: str) -> bool:
    try:
        client.get_model_version_by_alias(MODEL_NAME, alias)
        return True
    except mlflow.exceptions.MlflowException:
        return False


def run_training() -> dict:
    logging.basicConfig(level=logging.INFO)
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    df = load_training_data()
    if len(df) < 100:
        logger.error("För lite träningsdata (%d rader). Samla mer data.", len(df))
        return {"status": "skipped", "rows": len(df)}

    pipeline, metrics = train_model(df)

    with mlflow.start_run() as run:
        mlflow.log_params({
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 4,
        })
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )
        run_id = run.info.run_id

    client = MlflowClient()
    versions = client.search_model_versions(f"run_id='{run_id}'")
    new_version = max(v.version for v in versions)
    status = _promote_if_better(client, new_version, metrics["r2"])

    return {"status": status, "run_id": run_id, "version": new_version, **metrics}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_training()
    if result["status"] == "skipped":
        sys.exit(1)
    print(
        f"Status: {result['status']} | v{result['version']} | "
        f"R²: {result['r2']:.3f} | MAE: {result['mae']:.1f}",
        file=sys.stderr,
    )

