"""
Streamlit-dashboard för SafeDrive Analytics.

Visualiserar samband mellan väder och trafikflöde i Sverige.
Inkluderar ML-modellprestanda, prediktion och träningshistorik.
"""

import os
from datetime import datetime

import mlflow
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import requests
import streamlit as st
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

load_dotenv()

API_URL = os.environ.get("API_URL", "http://api:8000")
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "SafeDriveModel")

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
            traffic_site_id,
            county,
            latitude,
            longitude,
            vehicle_flow,
            average_speed,
            temperature_c,
            precipitation_mm,
            wind_speed_ms,
            snow_depth_cm,
            road_condition_code
        FROM ml_features
        WHERE measured_at >= NOW() - INTERVAL '7 days'
        ORDER BY measured_at DESC
        LIMIT 50000
        """,
        conn,
    )


@st.cache_data(ttl=60)
def fetch_model_health() -> dict:
    """Hämtar modellstatus från FastAPI /health."""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


@st.cache_data(ttl=300)
def fetch_training_history() -> pd.DataFrame:
    """Hämtar alla träningskörningar från MLflow och returnerar som DataFrame."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        experiment = client.get_experiment_by_name("safedriveanalytics")
        if experiment is None:
            return pd.DataFrame()
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time ASC"],
            max_results=200,
        )
        rows = []
        for run in runs:
            m = run.data.metrics
            if "r2" not in m:
                continue
            rows.append(
                {
                    "run_id": run.info.run_id[:8],
                    "started_at": datetime.fromtimestamp(run.info.start_time / 1000),
                    "r2": m.get("r2"),
                    "mae": m.get("mae"),
                    "training_rows": m.get("training_rows"),
                }
            )
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_champion_version() -> str | None:
    """Returnerar champion-versionsnumret från MLflow registry."""
    try:
        client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        champion = client.get_model_version_by_alias(MLFLOW_MODEL_NAME, "champion")
        return champion.version
    except Exception:
        return None


def _predict(payload: dict) -> dict | None:
    try:
        resp = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"Prediktion misslyckades: {exc}")
        return None


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
    health = fetch_model_health()
    champion_version = fetch_champion_version()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Mätpunkter (7d)", f"{len(df):,}")
    col2.metric("Medelflöde (fordon/h)", f"{df['vehicle_flow'].mean():.0f}")
    col3.metric("Medeltemperatur (°C)", f"{df['temperature_c'].mean():.1f}")
    col4.metric("Aktiva mätplatser", str(df['traffic_site_id'].nunique()))
    model_status = "✅ Laddad" if health.get("model_loaded") else "⚠️ Ej laddad"
    col5.metric("Champion-modell", f"v{champion_version}" if champion_version else "–", delta=model_status)

    st.divider()

    # ── ML-modellprestanda ───────────────────────────────────────────────────
    st.header("ML-modell: Champion vs träningshistorik")
    history_df = fetch_training_history()

    if not history_df.empty:
        col_hist, col_metrics = st.columns([2, 1])

        with col_hist:
            st.subheader("R² per träningskörning")
            fig_r2 = px.line(
                history_df,
                x="started_at",
                y="r2",
                markers=True,
                labels={"started_at": "Tränad", "r2": "R²"},
                title="Modellkvalitet över tid (högre = bättre)",
            )
            fig_r2.add_hline(
                y=history_df["r2"].max(),
                line_dash="dot",
                line_color="green",
                annotation_text=f"Bäst: {history_df['r2'].max():.3f}",
            )
            fig_r2.update_yaxes(range=[0, 1])
            st.plotly_chart(fig_r2, use_container_width=True)

        with col_metrics:
            st.subheader("Senaste champion")
            latest = history_df.iloc[-1]
            st.metric("R² (förklaringsgrad)", f"{latest['r2']:.3f}")
            if latest["mae"] is not None:
                st.metric("MAE (fel i fordon/h)", f"{latest['mae']:.1f}")
            if latest["training_rows"] is not None:
                st.metric("Träningsrader", f"{int(latest['training_rows']):,}")
            st.metric("Antal versioner", str(len(history_df)))

            st.subheader("Träningsdata (rader)")
            if history_df["training_rows"].notna().any():
                fig_rows = px.bar(
                    history_df.dropna(subset=["training_rows"]),
                    x="started_at",
                    y="training_rows",
                    labels={"started_at": "Tränad", "training_rows": "Rader"},
                )
                st.plotly_chart(fig_rows, use_container_width=True)
    else:
        st.info("Ingen träningshistorik hittad i MLflow ännu.")

    st.divider()

    # ── Prediktion ───────────────────────────────────────────────────────────
    st.header("Gör en prediktion")
    st.caption(f"Modell: SafeDriveModel@champion (v{health.get('model_version', '?')})")

    with st.form("prediction_form"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            temperature_c = st.slider("Temperatur (°C)", -25.0, 35.0, 5.0, 0.5)
            precipitation_mm = st.slider("Nederbörd (mm)", 0.0, 50.0, 0.0, 0.5)
        with col_b:
            wind_speed_ms = st.slider("Vindhastighet (m/s)", 0.0, 30.0, 3.0, 0.5)
            snow_depth_cm = st.slider("Snödjup (cm)", 0.0, 100.0, 0.0, 1.0)
        with col_c:
            road_condition_code = st.selectbox(
                "Väglag",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Normalt", 2: "Vått", 3: "Isigt", 4: "Snö"}[x],
            )
            hour_of_day = st.slider("Timme på dygnet", 0, 23, datetime.now().hour)
            day_of_week = st.selectbox(
                "Veckodag",
                options=list(range(7)),
                index=datetime.now().weekday(),
                format_func=lambda x: ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"][x],
            )
            month = st.selectbox("Månad", options=list(range(1, 13)), index=datetime.now().month - 1)

        submitted = st.form_submit_button("Prediktera trafikflöde", type="primary")

    if submitted:
        payload = {
            "temperature_c": temperature_c,
            "precipitation_mm": precipitation_mm,
            "wind_speed_ms": wind_speed_ms,
            "snow_depth_cm": snow_depth_cm,
            "road_condition_code": road_condition_code,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "month": month,
        }
        result = _predict(payload)
        if result:
            flow = result["predicted_vehicle_flow"]
            version = result["model_version"]
            st.success(f"Predikterat trafikflöde: **{flow:.0f} fordon/timme** (modell v{version})")

            # Jämför med medelvärde i datan
            avg_flow = df["vehicle_flow"].mean()
            diff_pct = (flow - avg_flow) / avg_flow * 100
            if diff_pct > 5:
                st.info(f"Det är {diff_pct:.0f}% högre än genomsnittet ({avg_flow:.0f} fordon/h) de senaste 7 dagarna.")
            elif diff_pct < -5:
                st.info(f"Det är {abs(diff_pct):.0f}% lägre än genomsnittet ({avg_flow:.0f} fordon/h) de senaste 7 dagarna.")
            else:
                st.info(f"Det är nära genomsnittet ({avg_flow:.0f} fordon/h) de senaste 7 dagarna.")

    st.divider()

    # ── Väder vs trafik ──────────────────────────────────────────────────────
    st.header("Väder- och trafikanalys")
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
