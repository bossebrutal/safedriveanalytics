"""
Ingestion-pipeline för SMHI väderdata.

Hämtar observationer från SMHI och lagrar dem i databasen.
Körs av Airflow men kan även anropas standalone.
"""

import logging
import os

import psycopg2
from dotenv import load_dotenv

from ingestion.smhi.smhi_client import (
    PARAMETER_AIR_TEMPERATURE,
    PARAMETER_PRECIPITATION,
    PARAMETER_SNOW_DEPTH,
    PARAMETER_WIND_SPEED,
    SmhiClient,
    WeatherObservation,
)

load_dotenv()
logger = logging.getLogger(__name__)

PARAMETERS_TO_INGEST = [
    PARAMETER_AIR_TEMPERATURE,
    PARAMETER_PRECIPITATION,
    PARAMETER_WIND_SPEED,
    PARAMETER_SNOW_DEPTH,
]


def get_db_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def insert_observations(
    conn: psycopg2.extensions.connection,
    observations: list[WeatherObservation],
) -> int:
    """Infogar observationer i databasen. Returnerar antal infogade rader."""
    if not observations:
        return 0

    sql = """
        INSERT INTO weather_observations
            (station_id, station_name, parameter, value, unit, observed_at, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (station_id, parameter, observed_at) DO NOTHING
    """
    rows = [
        (
            obs.station_id,
            obs.station_name,
            obs.parameter,
            obs.value,
            obs.unit,
            obs.timestamp,
            obs.latitude,
            obs.longitude,
        )
        for obs in observations
    ]

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()

    inserted = len(rows)
    logger.info("Infogade %d väderobservationer i databasen", inserted)
    return inserted


def run_ingestion(max_stations: int | None = None) -> int:
    """
    Kör hela SMHI-ingestionspipelinen.
    Returnerar totalt antal infogade rader.
    """
    client = SmhiClient()
    conn = get_db_connection()
    total = 0

    try:
        for parameter in PARAMETERS_TO_INGEST:
            logger.info("Hämtar observationer för parameter %s", parameter)
            observations = client.get_all_latest_observations(
                parameter, max_stations=max_stations
            )
            total += insert_observations(conn, observations)
    finally:
        conn.close()

    logger.info("SMHI-ingestion klar. Totalt %d rader inlagda.", total)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_ingestion()
