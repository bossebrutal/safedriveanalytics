-- SafeDrive Analytics - Databasschema
-- Kors automatiskt av PostgreSQL via docker-entrypoint-initdb.d/

-- Vaderobservationer (fran SMHI)
CREATE TABLE IF NOT EXISTS weather_observations (
    id              BIGSERIAL PRIMARY KEY,
    station_id      INTEGER       NOT NULL,
    station_name    VARCHAR(100),
    parameter       INTEGER       NOT NULL,  -- 1=temp, 4=vind, 5=nederbord, 8=sno
    value           DOUBLE PRECISION NOT NULL,
    unit            VARCHAR(20),
    observed_at     TIMESTAMPTZ   NOT NULL,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_weather_obs UNIQUE (station_id, parameter, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_weather_obs_observed_at
    ON weather_observations (observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_weather_obs_parameter
    ON weather_observations (parameter);

CREATE INDEX IF NOT EXISTS idx_weather_obs_location
    ON weather_observations (latitude, longitude);

COMMENT ON TABLE weather_observations IS
    'Vaderobservationer fran SMHI Open Data API. Uppdateras varje timme.';

-- Trafikflodesmastningar (fran Trafikverket TrafficFlow)
CREATE TABLE IF NOT EXISTS traffic_measurements (
    id              BIGSERIAL PRIMARY KEY,
    site_id         INTEGER       NOT NULL,  -- TrafficFlow.SiteId
    county          VARCHAR(10),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    vehicle_flow    INTEGER,                  -- Fordon per timme
    average_speed   DOUBLE PRECISION,         -- km/h
    measured_at     TIMESTAMPTZ   NOT NULL,
    ingested_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_traffic_measurement UNIQUE (site_id, measured_at)
);

CREATE INDEX IF NOT EXISTS idx_traffic_measured_at
    ON traffic_measurements (measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_traffic_county
    ON traffic_measurements (county);

CREATE INDEX IF NOT EXISTS idx_traffic_location
    ON traffic_measurements (latitude, longitude);

COMMENT ON TABLE traffic_measurements IS
    'Trafikflodesmastningar (TrafficFlow) fran Trafikverkets API. Uppdateras var 15:e minut.';

-- Vaglagsrapporter (fran Trafikverket RoadCondition)
-- Anvands istallet for Situation (kravde konto) - tillganglig med demokey
CREATE TABLE IF NOT EXISTS road_conditions (
    id              BIGSERIAL PRIMARY KEY,
    condition_id    VARCHAR(100)  NOT NULL UNIQUE,  -- RoadCondition.Id
    road_number     VARCHAR(100),
    county          VARCHAR(10),
    condition_code  INTEGER,  -- 1=normalt, 2=vatt, 3=isigt, 4=sno
    condition_text  VARCHAR(100),
    start_time      TIMESTAMPTZ   NOT NULL,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_road_conditions_start_time
    ON road_conditions (start_time DESC);

CREATE INDEX IF NOT EXISTS idx_road_conditions_road
    ON road_conditions (road_number, county);

COMMENT ON TABLE road_conditions IS
    'Vaglagsrapporter (RoadCondition) fran Trafikverkets API. '
    'ConditionCode: 1=normalt, 2=vatt, 3=isigt, 4=sno.';

-- ML features (sammanslagen vader + trafik)
CREATE TABLE IF NOT EXISTS ml_features (
    id                      BIGSERIAL PRIMARY KEY,
    traffic_site_id         INTEGER      NOT NULL,
    measured_at             TIMESTAMPTZ  NOT NULL,
    county                  VARCHAR(10),
    latitude                DOUBLE PRECISION,
    longitude               DOUBLE PRECISION,

    -- Trafikdata
    vehicle_flow            INTEGER,
    average_speed           DOUBLE PRECISION,

    -- Vaderdata (narmaste station inom 30 km)
    temperature_c           DOUBLE PRECISION,
    precipitation_mm        DOUBLE PRECISION,
    wind_speed_ms           DOUBLE PRECISION,
    snow_depth_cm           DOUBLE PRECISION,

    -- Vaglag (fran RoadCondition)
    road_condition_code     INTEGER DEFAULT 1,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ml_feature UNIQUE (traffic_site_id, measured_at)
);

CREATE INDEX IF NOT EXISTS idx_ml_features_measured_at
    ON ml_features (measured_at DESC);

COMMENT ON TABLE ml_features IS
    'Sammanslagen feature-tabell for ML-modelltraning. '
    'Vader matchas geografiskt (<=30 km) och tidsmassigt (+/-1 h) mot trafikmastpunkter.';
