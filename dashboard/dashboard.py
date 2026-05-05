"""
Streamlit-dashboard för SafeDrive Analytics.

Visualiserar samband mellan väder och trafikflöde i Sverige.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="SafeDrive Analytics",
    page_icon="🚗",
    layout="wide",
)


@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


@st.cache_data(ttl=300)
def load_features() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(
        """
        SELECT
            measured_at,
            road_number,
            county,
            latitude,
            longitude,
            vehicle_flow,
            average_speed,
            temperature_c,
            precipitation_mm,
            wind_speed_ms,
            snow_depth_cm,
            incident_count
        FROM ml_features
        WHERE measured_at >= NOW() - INTERVAL '7 days'
        ORDER BY measured_at DESC
        LIMIT 50000
        """,
        conn,
    )


def main():
    st.title("SafeDrive Analytics")
    st.subheader("Hur påverkar vädret trafikflödet i Sverige?")

    try:
        df = load_features()
    except Exception as exc:
        st.error(f"Kunde inte hämta data: {exc}")
        st.info("Kontrollera att databasen är igång och att .env är korrekt konfigurerad.")
        return

    if df.empty:
        st.warning("Ingen data hittades. Kontrollera att ingestion-pipelines har körts.")
        return

    # ── Nyckeltal ───────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mätpunkter (7d)", f"{len(df):,}")
    col2.metric("Medelflöde (fordon/h)", f"{df['vehicle_flow'].mean():.0f}")
    col3.metric("Medeltemperatur (°C)", f"{df['temperature_c'].mean():.1f}")
    col4.metric("Aktiva incidenter", f"{df['incident_count'].sum():.0f}")

    st.divider()

    # ── Temperatur vs trafikflöde ────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Temperatur vs Trafikflöde")
        fig = px.scatter(
            df.sample(min(5000, len(df))),
            x="temperature_c",
            y="vehicle_flow",
            color="precipitation_mm",
            color_continuous_scale="Blues",
            labels={
                "temperature_c": "Temperatur (°C)",
                "vehicle_flow": "Fordon/timme",
                "precipitation_mm": "Nederbörd (mm)",
            },
            opacity=0.5,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Vindhastighet vs Medelhastighet")
        fig2 = px.scatter(
            df.sample(min(5000, len(df))),
            x="wind_speed_ms",
            y="average_speed",
            color="snow_depth_cm",
            color_continuous_scale="ice",
            labels={
                "wind_speed_ms": "Vindhastighet (m/s)",
                "average_speed": "Medelhastighet (km/h)",
                "snow_depth_cm": "Snödjup (cm)",
            },
            opacity=0.5,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Trafikflöde per timme ────────────────────────────────────────────────
    st.subheader("Genomsnittligt trafikflöde per timme på dygnet")
    hourly = (
        df.assign(hour=df["measured_at"].dt.hour)
        .groupby("hour")["vehicle_flow"]
        .mean()
        .reset_index()
    )
    fig3 = px.bar(
        hourly,
        x="hour",
        y="vehicle_flow",
        labels={"hour": "Timme", "vehicle_flow": "Genomsnittligt antal fordon/h"},
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Karta ────────────────────────────────────────────────────────────────
    st.subheader("Geografisk spridning av mätpunkter")
    map_df = df[["latitude", "longitude", "vehicle_flow"]].dropna()
    if not map_df.empty:
        st.map(map_df.rename(columns={"latitude": "lat", "longitude": "lon"}))


if __name__ == "__main__":
    main()
