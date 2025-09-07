import streamlit as st
import pandas as pd
import clickhouse_connect
import pydeck as pdk
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="CrisisPulse", layout="wide")

# ---- Sidebar ----
st.sidebar.title("⚙️ Controls")
severity_min, severity_max = st.sidebar.slider(
    "Filter by severity", 0.0, 1.0, (0.0, 1.0), 0.05
)
source_filter = st.sidebar.text_input("Filter by source (leave blank for all)")
st.sidebar.markdown("---")
st.sidebar.markdown("🔗 [GitHub Repo](https://github.com/anav94/crisispulse)")
st.sidebar.markdown("🔗 [Live Demo](https://crisispulse-api-uopa.onrender.com)")

# ---- Header ----
st.markdown(
    """
    <div style="padding:15px; background-color:#0e1117; border-radius:10px;">
        <h1 style="color:#fafafa; margin:0;">🌍 CrisisPulse Dashboard</h1>
        <p style="color:#bbb; margin:0;">Real-time disaster intelligence — powered by ClickHouse & Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- DB connection ----
client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="default",
    password="Anav_1738",
    database="crisispulse"
)

query = """
    SELECT id, source, title, magnitude, severity, occurred_ts, lat, lon
    FROM incidents
    ORDER BY occurred_ts DESC
    LIMIT 200
"""
result = client.query(query)
df = pd.DataFrame(result.result_rows, columns=result.column_names)

# Fix serialization
for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].astype(str)
    if "ts" in col.lower():
        df[col] = pd.to_datetime(df[col], errors="coerce")

# Apply filters
df = df[(df["severity"].between(severity_min, severity_max))]
if source_filter:
    df = df[df["source"].str.contains(source_filter, case=False, na=False)]

# ---- Alerts ----
if not df.empty and (df["severity"] >= 0.8).any():
    st.error("🚨 High severity incident detected! Check latest events immediately.")

# ---- Metrics row ----
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Incidents", len(df))
with col2:
    st.metric("Avg Severity", round(df["severity"].mean(), 2) if not df.empty else 0)
with col3:
    st.metric("Max Magnitude", round(df["magnitude"].max(), 2) if not df.empty else 0)

# ---- Table ----
st.subheader("📋 Latest Incidents")
if not df.empty:
    def highlight_severity(val):
        if val < 0.3:
            return "background-color: lightgreen"
        elif val < 0.6:
            return "background-color: khaki"
        else:
            return "background-color: salmon"
    st.dataframe(df.style.applymap(highlight_severity, subset=["severity"]))
else:
    st.info("No incidents found.")

# ---- Severity over time (Altair) ----
st.subheader("📈 Severity Over Time")
if not df.empty:
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x="occurred_ts:T",
            y="severity:Q",
            tooltip=["title", "severity", "occurred_ts"]
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

# ---- Map ----
st.subheader("🗺️ Incident Map")
if not df.empty and {"lat", "lon"}.issubset(df.columns):
    df_map = df.dropna(subset=["lat", "lon"]).copy()
    df_map["color"] = df_map["severity"].apply(
        lambda s: [int(255 * s), int(255 * (1 - s)), 0, 180] if pd.notna(s) else [200, 200, 200, 100]
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius=50000,
        pickable=True,
        get_tooltip=["title", "severity"]
    )

    view_state = pdk.ViewState(
        latitude=df_map["lat"].mean(),
        longitude=df_map["lon"].mean(),
        zoom=2,
        pitch=0,
    )

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))