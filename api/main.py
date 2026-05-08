"""
FastAPI – REST API för SafeDrive Analytics ML-modellen.

Endpoints:
  POST /predict  – Prediktera trafikflöde givet väderförhållanden
  GET  /health   – Hälsokontroll

Modell laddas från MLflow Model Registry (Production-stage).
Bakgrundsuppgift kontrollerar ny version var MODEL_RELOAD_INTERVAL sekund.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import mlflow.sklearn
from fastapi import FastAPI, HTTPException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel, Field

import mlflow

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "SafeDriveModel")
MODEL_RELOAD_INTERVAL = int(os.environ.get("MODEL_RELOAD_INTERVAL", 300))  # sekunder

_model = None
_model_version = None


async def _load_model_from_registry() -> None:
    """Laddar @champion-modellen från MLflow om en ny version finns."""
    global _model, _model_version
    try:
        client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        champion = client.get_model_version_by_alias(MLFLOW_MODEL_NAME, "champion")
        latest_version = champion.version
        if latest_version == _model_version:
            return  # Redan laddad – inget att göra
        model_uri = f"models:/{MLFLOW_MODEL_NAME}@champion"
        loaded = await asyncio.to_thread(mlflow.sklearn.load_model, model_uri)
        _model = loaded
        _model_version = latest_version
        logger.info("Modell v%s (@champion) laddad från MLflow.", _model_version)
    except mlflow.exceptions.MlflowException:
        logger.warning("Ingen @champion-modell i MLflow registry ännu.")
    except Exception as exc:
        logger.error("Kunde inte ladda modell från MLflow: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    await _load_model_from_registry()

    async def _reload_loop():
        while True:
            await asyncio.sleep(MODEL_RELOAD_INTERVAL)
            await _load_model_from_registry()

    task = asyncio.create_task(_reload_loop())
    yield
    task.cancel()
    global _model, _model_version
    _model = None
    _model_version = None


app = FastAPI(
    title="SafeDrive Analytics API",
    description="Predikterar trafikflöde baserat på väderförhållanden i Sverige.",
    version="1.0.0",
    lifespan=lifespan,
)


class PredictionRequest(BaseModel):
    temperature_c: float = Field(..., description="Lufttemperatur i Celsius", examples=[5.0])
    precipitation_mm: float = Field(
        default=0.0, ge=0, description="Nederbördsmängd i mm", examples=[0.0]
    )
    wind_speed_ms: float = Field(
        default=0.0, ge=0, description="Vindhastighet m/s", examples=[3.5]
    )
    snow_depth_cm: float = Field(
        default=0.0, ge=0, description="Snödjup i cm", examples=[0.0]
    )
    road_condition_code: int = Field(
        default=1, ge=1, le=4, description="Väglagskod (1=normalt, 2=vått, 3=isigt, 4=snö)", examples=[1]
    )
    hour_of_day: int = Field(..., ge=0, le=23, description="Timme på dygnet (0-23)", examples=[8])
    day_of_week: int = Field(
        ..., ge=0, le=6, description="Veckodag (0=söndag, 6=lördag)", examples=[1]
    )
    month: int = Field(..., ge=1, le=12, description="Månad (1-12)", examples=[1])


class PredictionResponse(BaseModel):
    predicted_vehicle_flow: float = Field(
        ..., description="Predikterat antal fordon per timme"
    )
    model_version: str


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "model_loaded": _model is not None, "model_version": _model_version}


@app.post("/predict", response_model=PredictionResponse, tags=["prediction"])
def predict(request: PredictionRequest):
    if _model is None:
        raise HTTPException(
            status_code=503,
            detail="ML-modell ej laddad. Kontakta systemadministratören.",
        )

    import pandas as pd

    features = pd.DataFrame(
        [
            {
                "temperature_c": request.temperature_c,
                "precipitation_mm": request.precipitation_mm,
                "wind_speed_ms": request.wind_speed_ms,
                "snow_depth_cm": request.snow_depth_cm,
                "road_condition_code": request.road_condition_code,
                "hour_of_day": request.hour_of_day,
                "day_of_week": request.day_of_week,
                "month": request.month,
            }
        ]
    )

    prediction = float(_model.predict(features)[0])
    prediction = max(0.0, prediction)

    return PredictionResponse(
        predicted_vehicle_flow=round(prediction, 1),
        model_version=str(_model_version),
    )

