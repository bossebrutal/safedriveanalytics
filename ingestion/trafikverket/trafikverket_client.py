"""
Trafikverket Open API-klient.

Hämtar trafikflödesdata och väglagsdata via Trafikverkets öppna API.
Dokumentation: https://data.trafikverket.se/documentation/datacache/data-model

API-nyckel: Gratis via https://data.trafikverket.se/documentation/datacache/intro
Utan nyckel används "demokey" som fungerar för testning och lägre volymer.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# Demokey fungerar utan konto – för produktion, registrera egen nyckel
DEFAULT_API_KEY = "demokey"

# RoadCondition-koder (ConditionCode)
CONDITION_NORMAL = 1
CONDITION_WET = 2
CONDITION_ICY = 3
CONDITION_SNOW = 4


@dataclass
class TrafficMeasurement:
    site_id: int
    county: str
    latitude: float
    longitude: float
    vehicle_flow: int       # Fordon per timme
    average_speed: float    # km/h
    measurement_time: datetime


@dataclass
class RoadConditionObservation:
    condition_id: str
    road_number: str
    county: str
    condition_code: int     # 1=normalt, 2=vått, 3=isigt, 4=snö
    condition_text: str
    start_time: datetime
    latitude: float
    longitude: float


class TrafikverketClient:
    """
    Klient för Trafikverkets Open API.

    Standardnyckel är "demokey" (ingen registrering krävs).
    Registrera gratis nyckel på data.trafikverket.se för högre volymer.
    """

    def __init__(
        self,
        api_key: str = DEFAULT_API_KEY,
        session: requests.Session | None = None,
        timeout: int = 30,
    ):
        self._api_key = api_key or DEFAULT_API_KEY
        self._session = session or requests.Session()
        self._timeout = timeout

    def _post(self, xml_query: str) -> dict:
        """Skickar en XML-fråga till Trafikverkets API och returnerar JSON."""
        response = self._session.post(
            TRAFIKVERKET_API_URL,
            data=xml_query.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_traffic_flow(self, county_no: int | None = None) -> list[TrafficMeasurement]:
        """
        Hämtar senaste trafikflödesmätningar (objecttype: TrafficFlow).
        county_no: länskod som heltal, t.ex. 1 för Stockholm (valfritt filter).
        """
        county_filter = ""
        if county_no is not None:
            county_filter = f'<EQ name="CountyNo" value="{county_no}"/>'

        query = f"""
        <REQUEST>
          <LOGIN authenticationkey="{self._api_key}"/>
          <QUERY objecttype="TrafficFlow" schemaversion="1.4" limit="500">
            <FILTER>
              <EQ name="VehicleType" value="anyVehicle"/>
              {county_filter}
            </FILTER>
            <INCLUDE>SiteId</INCLUDE>
            <INCLUDE>CountyNo</INCLUDE>
            <INCLUDE>Geometry.WGS84</INCLUDE>
            <INCLUDE>VehicleFlowRate</INCLUDE>
            <INCLUDE>AverageVehicleSpeed</INCLUDE>
            <INCLUDE>MeasurementTime</INCLUDE>
          </QUERY>
        </REQUEST>
        """

        data = self._post(query)
        results = data.get("RESPONSE", {}).get("RESULT", [{}])[0]
        raw_items = results.get("TrafficFlow", [])

        measurements = []
        for item in raw_items:
            try:
                coords = self._parse_wgs84(item.get("Geometry", {}).get("WGS84", ""))
                measurements.append(
                    TrafficMeasurement(
                        site_id=int(item["SiteId"]),
                        county=str(item.get("CountyNo", "")),
                        latitude=coords[0],
                        longitude=coords[1],
                        vehicle_flow=int(item.get("VehicleFlowRate", 0) or 0),
                        average_speed=float(item.get("AverageVehicleSpeed", 0.0) or 0.0),
                        measurement_time=datetime.fromisoformat(
                            item["MeasurementTime"].replace("Z", "+00:00")
                        ),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                logger.debug("Hoppade över TrafficFlow-post pga parse-fel: %s", exc)
                continue

        logger.info("Hämtade %d trafikflödesmätningar", len(measurements))
        return measurements

    def get_road_conditions(self) -> list[RoadConditionObservation]:
        """
        Hämtar aktuella väglagsrapporter (objecttype: RoadCondition).
        Väglag (is, snö, blött, normalt) är direkt relevant för väderpåverkan.
        """
        query = f"""
        <REQUEST>
          <LOGIN authenticationkey="{self._api_key}"/>
          <QUERY objecttype="RoadCondition" schemaversion="1" limit="500">
            <FILTER></FILTER>
            <INCLUDE>Id</INCLUDE>
            <INCLUDE>ConditionCode</INCLUDE>
            <INCLUDE>ConditionText</INCLUDE>
            <INCLUDE>CountyNo</INCLUDE>
            <INCLUDE>RoadNumber</INCLUDE>
            <INCLUDE>StartTime</INCLUDE>
            <INCLUDE>Geometry.WGS84</INCLUDE>
          </QUERY>
        </REQUEST>
        """

        data = self._post(query)
        results = data.get("RESPONSE", {}).get("RESULT", [{}])[0]
        raw_items = results.get("RoadCondition", [])

        conditions = []
        for item in raw_items:
            try:
                coords = self._parse_wgs84_linestring(item.get("Geometry", {}).get("WGS84", ""))
                conditions.append(
                    RoadConditionObservation(
                        condition_id=item.get("Id", ""),
                        road_number=item.get("RoadNumber", ""),
                        county=str(item.get("CountyNo", "")),
                        condition_code=int(item.get("ConditionCode", 1)),
                        condition_text=item.get("ConditionText", ""),
                        start_time=datetime.fromisoformat(
                            item["StartTime"].replace("Z", "+00:00")
                        ),
                        latitude=coords[0],
                        longitude=coords[1],
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                logger.debug("Hoppade över RoadCondition-post pga parse-fel: %s", exc)
                continue

        logger.info("Hämtade %d väglagsrapporter", len(conditions))
        return conditions

    @staticmethod
    def _parse_wgs84(wgs84_str: str) -> tuple[float, float]:
        """
        Parsar WGS84 POINT-sträng: 'POINT (lon lat)' → (lat, lon).
        Returnerar (0.0, 0.0) vid fel.
        """
        try:
            coords = wgs84_str.replace("POINT (", "").replace(")", "").split()
            return float(coords[1]), float(coords[0])
        except (IndexError, ValueError, AttributeError):
            return 0.0, 0.0

    @staticmethod
    def _parse_wgs84_linestring(wgs84_str: str) -> tuple[float, float]:
        """
        Parsar WGS84 LINESTRING: 'LINESTRING (lon1 lat1, lon2 lat2, ...)' → mittpunkt (lat, lon).
        Faller tillbaka på _parse_wgs84 om det är ett POINT.
        """
        try:
            if wgs84_str.startswith("POINT"):
                return TrafikverketClient._parse_wgs84(wgs84_str)
            inner = wgs84_str.replace("LINESTRING (", "").replace(")", "")
            pairs = [p.strip().split() for p in inner.split(",") if p.strip()]
            mid = pairs[len(pairs) // 2]
            return float(mid[1]), float(mid[0])
        except (IndexError, ValueError, AttributeError):
            return 0.0, 0.0
