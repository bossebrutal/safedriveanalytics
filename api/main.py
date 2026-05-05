"""
FastAPI – REST API för SafeDrive Analytics ML-modellen.

Endpoints:
  POST /predict  – Prediktera trafikflöde givet väderförhållanden
  GET  /health   – Hälsokontroll
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model
    from ml_model.train import MODEL_PATH, load_model

    try:
        _model = load_model(MODEL_PATH)
        logger.info("ML-modell laddad från %s", MODEL_PATH)
    except FileNotFoundError:
        logger.error(
            "Modell saknas på %s. Kör ml_model/train.py för att träna modellen.", MODEL_PATH
        )
    yield
    _model = None


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
    return {"status": "ok", "model_loaded": _model is not None}


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
        model_version="1.0.0",
    )
