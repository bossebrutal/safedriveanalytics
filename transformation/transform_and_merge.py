"""
Dataomvandling och feature engineering.

Sammanfogar väder- och trafikdata baserat på geografisk och tidsmässig proximity.
Skapar den feature-tabell som ML-modellen tränas på.
"""

import logging
import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Max avstånd (km) för att koppla en vädermätstation till en trafikmätpunkt
MAX_DISTANCE_KM = 30

# Tidsfönster för matchning (senaste väderobservationen inom N timmar)
TIME_WINDOW_HOURS = 1


def get_db_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def run_transformation() -> int:
    """
    Sammanfogar väder och trafik i feature-tabellen.
    Returnerar antal nya rader i ml_features.
    """
    conn = get_db_connection()
    try:
        inserted = _merge_features(conn)
    finally:
        conn.close()
    logger.info("Transformation klar – %d nya feature-rader skapades", inserted)
    return inserted


def _merge_features(conn: psycopg2.extensions.connection) -> int:
    """
    Skapar/uppdaterar ml_features-tabellen med sammanslagen data.
    Matchar trafik- och vädermätningar geografiskt (haversine) och tidsmässigt.
    """
    sql = """
    INSERT INTO ml_features (
        traffic_site_id,
        measured_at,
        county,
        latitude,
        longitude,
        vehicle_flow,
        average_speed,
        temperature_c,
        precipitation_mm,
        wind_speed_ms,
        snow_depth_cm,
        road_condition_code,
        created_at
    )
    SELECT
        tm.site_id,
        tm.measured_at,
        tm.county,
        tm.latitude,
        tm.longitude,
        tm.vehicle_flow,
        tm.average_speed,
        w_temp.value   AS temperature_c,
        w_prec.value   AS precipitation_mm,
        w_wind.value   AS wind_speed_ms,
        w_snow.value   AS snow_depth_cm,
        COALESCE(rc.condition_code, 1) AS road_condition_code,
        NOW()
    FROM traffic_measurements tm

    -- Närmaste temperaturobservation (parameter 1) inom MAX_DISTANCE_KM och TIME_WINDOW_HOURS
    LEFT JOIN LATERAL (
        SELECT value
        FROM weather_observations
        WHERE parameter = 1
          AND observed_at BETWEEN tm.measured_at - INTERVAL '1 hour'
                               AND tm.measured_at + INTERVAL '1 hour'
          AND (
            6371 * acos(
              LEAST(1.0,
                cos(radians(tm.latitude)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(tm.longitude)) +
                sin(radians(tm.latitude)) * sin(radians(latitude))
              )
            )
          ) < %(max_km)s
        ORDER BY abs(extract(epoch from (observed_at - tm.measured_at)))
        LIMIT 1
    ) w_temp ON true

    LEFT JOIN LATERAL (
        SELECT value
        FROM weather_observations
        WHERE parameter = 5
          AND observed_at BETWEEN tm.measured_at - INTERVAL '1 hour'
                               AND tm.measured_at + INTERVAL '1 hour'
          AND (
            6371 * acos(
              LEAST(1.0,
                cos(radians(tm.latitude)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(tm.longitude)) +
                sin(radians(tm.latitude)) * sin(radians(latitude))
              )
            )
          ) < %(max_km)s
        ORDER BY abs(extract(epoch from (observed_at - tm.measured_at)))
        LIMIT 1
    ) w_prec ON true

    LEFT JOIN LATERAL (
        SELECT value
        FROM weather_observations
        WHERE parameter = 4
          AND observed_at BETWEEN tm.measured_at - INTERVAL '1 hour'
                               AND tm.measured_at + INTERVAL '1 hour'
          AND (
            6371 * acos(
              LEAST(1.0,
                cos(radians(tm.latitude)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(tm.longitude)) +
                sin(radians(tm.latitude)) * sin(radians(latitude))
              )
            )
          ) < %(max_km)s
        ORDER BY abs(extract(epoch from (observed_at - tm.measured_at)))
        LIMIT 1
    ) w_wind ON true

    LEFT JOIN LATERAL (
        SELECT value
        FROM weather_observations
        WHERE parameter = 8
          AND observed_at BETWEEN tm.measured_at - INTERVAL '1 hour'
                               AND tm.measured_at + INTERVAL '1 hour'
          AND (
            6371 * acos(
              LEAST(1.0,
                cos(radians(tm.latitude)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(tm.longitude)) +
                sin(radians(tm.latitude)) * sin(radians(latitude))
              )
            )
          ) < %(max_km)s
        ORDER BY abs(extract(epoch from (observed_at - tm.measured_at)))
        LIMIT 1
    ) w_snow ON true

    -- Närmaste väglagsrapport geografiskt vid mättillfället
    LEFT JOIN LATERAL (
        SELECT condition_code
        FROM road_conditions
        WHERE start_time <= tm.measured_at
          AND (
            6371 * acos(
              LEAST(1.0,
                cos(radians(tm.latitude)) * cos(radians(latitude)) *
                cos(radians(longitude) - radians(tm.longitude)) +
                sin(radians(tm.latitude)) * sin(radians(latitude))
              )
            )
          ) < %(max_km)s
        ORDER BY abs(extract(epoch from (start_time - tm.measured_at)))
        LIMIT 1
    ) rc ON true

    -- Hoppa över rader som redan finns
    WHERE NOT EXISTS (
        SELECT 1 FROM ml_features mf
        WHERE mf.traffic_site_id = tm.site_id
          AND mf.measured_at = tm.measured_at
    )
    -- Kräv minst temperaturdata
    AND w_temp.value IS NOT NULL

    ORDER BY tm.measured_at DESC
    LIMIT 10000
    ON CONFLICT (traffic_site_id, measured_at) DO NOTHING
    """

    with conn.cursor() as cur:
        cur.execute(sql, {"max_km": MAX_DISTANCE_KM})
        conn.commit()
        return cur.rowcount
