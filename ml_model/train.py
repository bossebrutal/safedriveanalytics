"""
ML-modellträning: Prediktera trafikflöde utifrån väderförhållanden.

Features: temperatur, nederbörd, vind, snödjup, timme, dag, incidenter
Target:   vehicle_flow (antal fordon/timme)
"""

import logging
import os
import sys

import joblib
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

load_dotenv()
logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")

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


def train_model(df: pd.DataFrame) -> Pipeline:
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
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    logger.info("Träning klar — MAE: %.1f fordon/h, R²: %.3f", mae, r2)
    print(f"MAE: {mae:.1f} fordon/h | R²: {r2:.3f}", file=sys.stderr)

    return pipeline


def save_model(pipeline: Pipeline, path: str = MODEL_PATH) -> None:
    joblib.dump(pipeline, path)
    logger.info("Modell sparad till %s", path)


def load_model(path: str = MODEL_PATH) -> Pipeline:
    return joblib.load(path)


def run_training() -> dict:
    logging.basicConfig(level=logging.INFO)
    df = load_training_data()
    if len(df) < 100:
        logger.error("För lite träningsdata (%d rader). Samla mer data först.", len(df))
        return {"status": "skipped", "rows": len(df)}
    pipeline = train_model(df)
    save_model(pipeline)
    return {"status": "ok", "rows": len(df)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = load_training_data()
    if len(df) < 100:
        logger.error("För lite träningsdata (%d rader). Samla mer data först.", len(df))
        sys.exit(1)
    pipeline = train_model(df)
    save_model(pipeline)
