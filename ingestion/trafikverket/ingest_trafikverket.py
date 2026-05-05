"""
Ingestion-pipeline för Trafikverket trafikdata.
"""

import logging
import os

import psycopg2
from dotenv import load_dotenv

from ingestion.trafikverket.trafikverket_client import (
    DEFAULT_API_KEY,
    RoadConditionObservation,
    TrafficMeasurement,
    TrafikverketClient,
)

load_dotenv()
logger = logging.getLogger(__name__)


def get_db_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def insert_traffic_measurements(
    conn: psycopg2.extensions.connection,
    measurements: list[TrafficMeasurement],
) -> int:
    if not measurements:
        return 0

    sql = """
        INSERT INTO traffic_measurements
            (site_id, county, latitude, longitude,
             vehicle_flow, average_speed, measured_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (site_id, measured_at) DO NOTHING
    """
    rows = [
        (
            m.site_id,
            m.county,
            m.latitude,
            m.longitude,
            m.vehicle_flow,
            m.average_speed,
            m.measurement_time,
        )
        for m in measurements
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    logger.info("Infogade %d trafikflödesmätningar", len(rows))
    return len(rows)


def insert_road_conditions(
    conn: psycopg2.extensions.connection,
    conditions: list[RoadConditionObservation],
) -> int:
    if not conditions:
        return 0

    sql = """
        INSERT INTO road_conditions
            (condition_id, road_number, county, condition_code,
             condition_text, start_time, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (condition_id) DO UPDATE SET
            condition_code = EXCLUDED.condition_code,
            condition_text = EXCLUDED.condition_text
    """
    rows = [
        (
            c.condition_id,
            c.road_number,
            c.county,
            c.condition_code,
            c.condition_text,
            c.start_time,
            c.latitude,
            c.longitude,
        )
        for c in conditions
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    logger.info("Infogade/uppdaterade %d väglagsrapporter", len(rows))
    return len(rows)


def run_ingestion() -> dict:
    """Kör hela Trafikverket-ingestionspipelinen. Returnerar statistik."""
    api_key = os.environ.get("TRAFIKVERKET_API_KEY", DEFAULT_API_KEY)
    client = TrafikverketClient(api_key=api_key)
    conn = get_db_connection()

    try:
        measurements = client.get_traffic_flow()
        conditions = client.get_road_conditions()

        n_measurements = insert_traffic_measurements(conn, measurements)
        n_conditions = insert_road_conditions(conn, conditions)
    finally:
        conn.close()

    result = {"measurements": n_measurements, "road_conditions": n_conditions}
    logger.info("Trafikverket-ingestion klar: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_ingestion()
