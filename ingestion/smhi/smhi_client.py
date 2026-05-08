"""
SMHI Open Data API-klient.

Hämtar väderobservationer från SMHI:s öppna API.
Dokumentation: https://opendata.smhi.se/apidocs/metobs/
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

SMHI_BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/latest"

# Parameternycklar för SMHI
PARAMETER_AIR_TEMPERATURE = 1      # Lufttemperatur (°C)
PARAMETER_PRECIPITATION = 5        # Nederbördsmängd (mm)
PARAMETER_WIND_SPEED = 4           # Vindhastighet (m/s)
PARAMETER_VISIBILITY = 12          # Sikt (m) – ej tillgänglig på alla stationer
PARAMETER_SNOW_DEPTH = 8           # Snödjup (cm)


@dataclass
class WeatherObservation:
    station_id: int
    station_name: str
    parameter: int
    value: float
    unit: str
    timestamp: datetime
    latitude: float
    longitude: float


class SmhiClient:
    """Klient för SMHI Open Data Meteorological Observations API."""

    def __init__(self, session: requests.Session | None = None, timeout: int = 30):
        self._session = session or requests.Session()
        self._timeout = timeout

    def get_stations(self, parameter: int) -> list[dict]:
        """Hämta alla mätstationer för en given parameter."""
        url = f"{SMHI_BASE_URL}/parameter/{parameter}/station.json"
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("station", [])

    def get_latest_observations(
        self, parameter: int, station_id: int,
        station_lat: float = 0.0, station_lon: float = 0.0
    ) -> list[WeatherObservation]:
        """
        Hämta senaste observationer för en station och parameter.
        Returnerar en lista med WeatherObservation-objekt.
        """
        url = (
            f"{SMHI_BASE_URL}/parameter/{parameter}"
            f"/station/{station_id}/period/latest-day/data.json"
        )
        try:
            response = self._session.get(url, timeout=self._timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.warning("Kunde inte hämta data för station %s: %s", station_id, exc)
            return []

        data = response.json()
        station_meta = data.get("station", {})
        unit = data.get("parameter", {}).get("unit", "")

        observations = []
        for entry in data.get("value", []):
            try:
                value = float(entry["value"])
                timestamp = datetime.utcfromtimestamp(entry["date"] / 1000)
            except (KeyError, ValueError, TypeError):
                continue
            obs = WeatherObservation(
                station_id=station_id,
                station_name=station_meta.get("name", ""),
                parameter=parameter,
                value=value,
                unit=unit,
                timestamp=timestamp,
                latitude=station_lat or station_meta.get("latitude", 0.0),
                longitude=station_lon or station_meta.get("longitude", 0.0),
            )
            observations.append(obs)

        logger.info(
            "Hämtade %d observationer från station %s (parameter %s)",
            len(observations),
            station_id,
            parameter,
        )
        return observations

    def get_all_latest_observations(
        self, parameter: int, max_stations: int | None = None
    ) -> list[WeatherObservation]:
        """
        Hämta senaste observationer från alla aktiva stationer för en parameter.
        max_stations begränsar antalet stationer (användbart vid test/dev).
        """
        stations = self.get_stations(parameter)
        active = [s for s in stations if s.get("active", False)]

        if max_stations:
            active = active[:max_stations]

        all_obs: list[WeatherObservation] = []
        for station in active:
            obs = self.get_latest_observations(
                parameter,
                station["id"],
                station_lat=station.get("latitude", 0.0),
                station_lon=station.get("longitude", 0.0),
            )
            all_obs.extend(obs)

        logger.info(
            "Totalt %d observationer hämtade (parameter %s, %d stationer)",
            len(all_obs),
            parameter,
            len(active),
        )
        return all_obs
