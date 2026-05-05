"""Tester för FastAPI-endpointsen."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestPredictEndpoint:
    VALID_PAYLOAD = {
        "temperature_c": 5.0,
        "precipitation_mm": 0.0,
        "wind_speed_ms": 3.5,
        "snow_depth_cm": 0.0,
        "incident_count": 0,
        "hour_of_day": 8,
        "day_of_week": 1,
        "month": 3,
    }

    def test_predict_without_model_returns_503(self, client):
        import api.main as api_module

        original_model = api_module._model
        api_module._model = None
        try:
            response = client.post("/predict", json=self.VALID_PAYLOAD)
            assert response.status_code == 503
        finally:
            api_module._model = original_model

    def test_predict_with_mock_model_returns_200(self, client):
        import api.main as api_module

        mock_model = MagicMock()
        mock_model.predict.return_value = [1234.5]
        api_module._model = mock_model

        try:
            response = client.post("/predict", json=self.VALID_PAYLOAD)
            assert response.status_code == 200
            data = response.json()
            assert "predicted_vehicle_flow" in data
            assert data["predicted_vehicle_flow"] == pytest.approx(1234.5)
        finally:
            api_module._model = None

    def test_predict_negative_output_clamped_to_zero(self, client):
        import api.main as api_module

        mock_model = MagicMock()
        mock_model.predict.return_value = [-100.0]
        api_module._model = mock_model

        try:
            response = client.post("/predict", json=self.VALID_PAYLOAD)
            assert response.json()["predicted_vehicle_flow"] == 0.0
        finally:
            api_module._model = None

    def test_predict_invalid_hour_returns_422(self, client):
        payload = {**self.VALID_PAYLOAD, "hour_of_day": 25}
        response = client.post("/predict", json=payload)
        assert response.status_code == 422

    def test_predict_negative_precipitation_returns_422(self, client):
        payload = {**self.VALID_PAYLOAD, "precipitation_mm": -1.0}
        response = client.post("/predict", json=payload)
        assert response.status_code == 422
