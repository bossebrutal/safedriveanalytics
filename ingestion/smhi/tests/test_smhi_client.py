"""Tester för SMHI-klienten."""

from datetime import datetime
from unittest.mock import MagicMock

import requests

from ingestion.smhi.smhi_client import (
    PARAMETER_AIR_TEMPERATURE,
    SmhiClient,
    WeatherObservation,
)

MOCK_STATIONS_RESPONSE = {
    "station": [
        {
            "id": 98210,
            "name": "Stockholm",
            "latitude": 59.35,
            "longitude": 18.05,
            "active": True,
        },
        {
            "id": 72420,
            "name": "Göteborg",
            "latitude": 57.71,
            "longitude": 12.0,
            "active": True,
        },
        {
            "id": 11111,
            "name": "Inaktiv station",
            "latitude": 60.0,
            "longitude": 15.0,
            "active": False,
        },
    ]
}

MOCK_OBSERVATIONS_RESPONSE = {
    "station": {"id": 98210, "name": "Stockholm", "latitude": 59.35, "longitude": 18.05},
    "parameter": {"unit": "°C"},
    "value": [
        {"date": 1700000000000, "value": "5.3"},
        {"date": 1700003600000, "value": "4.9"},
        {"date": 1700007200000, "value": "invalid"},  # Ska ignoreras
    ],
}


class TestSmhiClient:
    def setup_method(self):
        self.mock_session = MagicMock()
        self.client = SmhiClient(session=self.mock_session)

    def _mock_get(self, json_data: dict, status_code: int = 200):
        mock_response = MagicMock()
        mock_response.json.return_value = json_data
        mock_response.status_code = status_code
        mock_response.raise_for_status.return_value = None
        self.mock_session.get.return_value = mock_response
        return mock_response

    def test_get_stations_returns_list(self):
        self._mock_get(MOCK_STATIONS_RESPONSE)
        stations = self.client.get_stations(PARAMETER_AIR_TEMPERATURE)
        assert len(stations) == 3
        assert stations[0]["name"] == "Stockholm"

    def test_get_latest_observations_parses_values(self):
        self._mock_get(MOCK_OBSERVATIONS_RESPONSE)
        obs = self.client.get_latest_observations(PARAMETER_AIR_TEMPERATURE, 98210)
        # "invalid" ska filtreras bort
        assert len(obs) == 2
        assert all(isinstance(o, WeatherObservation) for o in obs)
        assert obs[0].value == 5.3
        assert obs[0].station_name == "Stockholm"
        assert obs[0].unit == "°C"

    def test_get_latest_observations_returns_empty_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        self.mock_session.get.return_value = mock_response
        result = self.client.get_latest_observations(PARAMETER_AIR_TEMPERATURE, 99999)
        assert result == []

    def test_get_all_latest_observations_filters_inactive_stations(self):
        # Första anropet: get_stations, andra anropet: data per station
        station_resp = MagicMock()
        station_resp.json.return_value = MOCK_STATIONS_RESPONSE
        station_resp.raise_for_status.return_value = None

        obs_resp = MagicMock()
        obs_resp.json.return_value = MOCK_OBSERVATIONS_RESPONSE
        obs_resp.raise_for_status.return_value = None

        self.mock_session.get.side_effect = [station_resp, obs_resp, obs_resp]

        self.client.get_all_latest_observations(PARAMETER_AIR_TEMPERATURE)
        # Ska bara hämta från 2 aktiva stationer
        assert self.mock_session.get.call_count == 3  # 1 stations + 2 aktiva

    def test_get_all_latest_observations_respects_max_stations(self):
        station_resp = MagicMock()
        station_resp.json.return_value = MOCK_STATIONS_RESPONSE
        station_resp.raise_for_status.return_value = None

        obs_resp = MagicMock()
        obs_resp.json.return_value = MOCK_OBSERVATIONS_RESPONSE
        obs_resp.raise_for_status.return_value = None

        self.mock_session.get.side_effect = [station_resp, obs_resp]

        self.client.get_all_latest_observations(
            PARAMETER_AIR_TEMPERATURE, max_stations=1
        )
        assert self.mock_session.get.call_count == 2  # 1 stations + 1 aktiv

    def test_observation_timestamp_is_datetime(self):
        self._mock_get(MOCK_OBSERVATIONS_RESPONSE)
        obs = self.client.get_latest_observations(PARAMETER_AIR_TEMPERATURE, 98210)
        assert isinstance(obs[0].timestamp, datetime)
