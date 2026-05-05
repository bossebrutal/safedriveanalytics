"""Tester för Trafikverket-klienten."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from ingestion.trafikverket.trafikverket_client import (
    DEFAULT_API_KEY,
    RoadConditionObservation,
    TrafficMeasurement,
    TrafikverketClient,
)

MOCK_FLOW_RESPONSE = {
    "RESPONSE": {
        "RESULT": [
            {
                "TrafficFlow": [
                    {
                        "SiteId": 40,
                        "CountyNo": 1,
                        "Geometry": {"WGS84": "POINT (18.06 59.33)"},
                        "VehicleFlowRate": 1200,
                        "AverageVehicleSpeed": 85.0,
                        "MeasurementTime": "2024-01-15T10:00:00Z",
                    },
                    {
                        "SiteId": 4306,
                        "CountyNo": 3,
                        "Geometry": {"WGS84": "POINT (17.65 59.86)"},
                        "VehicleFlowRate": 400,
                        "AverageVehicleSpeed": 90.0,
                        "MeasurementTime": "2024-01-15T10:05:00Z",
                    },
                ]
            }
        ]
    }
}

MOCK_CONDITION_RESPONSE = {
    "RESPONSE": {
        "RESULT": [
            {
                "RoadCondition": [
                    {
                        "Id": "RC-001",
                        "RoadNumber": "E4",
                        "CountyNo": "01",
                        "ConditionCode": 3,
                        "ConditionText": "Isigt",
                        "StartTime": "2024-01-15T08:00:00Z",
                        "Geometry": {"WGS84": "POINT (18.05 59.30)"},
                    }
                ]
            }
        ]
    }
}


class TestTrafikverketClient:
    def setup_method(self):
        self.mock_session = MagicMock()
        self.client = TrafikverketClient(session=self.mock_session)

    def _mock_post(self, json_data: dict):
        mock_response = MagicMock()
        mock_response.json.return_value = json_data
        mock_response.raise_for_status.return_value = None
        self.mock_session.post.return_value = mock_response

    def test_default_api_key_is_demokey(self):
        client = TrafikverketClient()
        assert client._api_key == DEFAULT_API_KEY

    def test_empty_api_key_falls_back_to_demokey(self):
        client = TrafikverketClient(api_key="")
        assert client._api_key == DEFAULT_API_KEY

    def test_get_traffic_flow_parses_measurements(self):
        self._mock_post(MOCK_FLOW_RESPONSE)
        result = self.client.get_traffic_flow()
        assert len(result) == 2
        assert all(isinstance(m, TrafficMeasurement) for m in result)
        assert result[0].site_id == 40
        assert result[0].vehicle_flow == 1200
        assert result[0].average_speed == 85.0
        assert result[0].latitude == pytest.approx(59.33, abs=0.01)

    def test_get_traffic_flow_timestamp_is_datetime(self):
        self._mock_post(MOCK_FLOW_RESPONSE)
        result = self.client.get_traffic_flow()
        assert isinstance(result[0].measurement_time, datetime)

    def test_get_road_conditions_parses_conditions(self):
        self._mock_post(MOCK_CONDITION_RESPONSE)
        result = self.client.get_road_conditions()
        assert len(result) == 1
        assert isinstance(result[0], RoadConditionObservation)
        assert result[0].condition_id == "RC-001"
        assert result[0].condition_code == 3
        assert result[0].condition_text == "Isigt"
        assert result[0].road_number == "E4"

    def test_parse_wgs84_valid(self):
        lat, lon = TrafikverketClient._parse_wgs84("POINT (18.06 59.33)")
        assert lat == pytest.approx(59.33)
        assert lon == pytest.approx(18.06)

    def test_parse_wgs84_invalid_returns_zero(self):
        lat, lon = TrafikverketClient._parse_wgs84("INVALID")
        assert lat == 0.0
        assert lon == 0.0

    def test_parse_wgs84_linestring_returns_midpoint(self):
        wgs84 = "LINESTRING (17.0 59.0, 18.0 60.0, 19.0 61.0)"
        lat, lon = TrafikverketClient._parse_wgs84_linestring(wgs84)
        # Mittpunkten är index 1 (18.0, 60.0)
        assert lat == pytest.approx(60.0)
        assert lon == pytest.approx(18.0)

    def test_get_traffic_flow_skips_malformed_entries(self):
        malformed_response = {
            "RESPONSE": {
                "RESULT": [
                    {
                        "TrafficFlow": [
                            # Saknar MeasurementTime – ska hoppas över
                            {"SiteId": 999, "VehicleFlowRate": 100},
                        ]
                    }
                ]
            }
        }
        self._mock_post(malformed_response)
        result = self.client.get_traffic_flow()
        assert result == []
