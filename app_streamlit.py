import streamlit as st
import pandas as pd
import clickhouse_connect

st.set_page_config(page_title="CrisisPulse", layout="wide")
st.title("🌍 CrisisPulse Dashboard")
st.markdown("Real-time disaster intelligence — powered by ClickHouse & Streamlit")

# Try ClickHouse connection
def get_data():
    try:
        client = clickhouse_connect.get_client(
            host="localhost",  # works locally
            port=8123,
            username="default",
            password="Anav_1738",
            database="crisispulse"
        )
        rows = client.query("""
            SELECT id, source, title, magnitude, severity, occurred_ts, lat, lon
            FROM incidents ORDER BY occurred_ts DESC LIMIT 100
        """).result_rows
        df = pd.DataFrame(rows, columns=[
            "id", "source", "title", "magnitude", "severity", "occurred_ts", "lat", "lon"
        ])
        return df
    except Exception:
        # Fallback synthetic demo data
        return pd.DataFrame([
            {"id": 1, "source": "synthetic", "title": "Earthquake near SF", "magnitude": 4.8, "severity": 0.62, "occurred_ts": "2025-09-07 10:00", "lat": 37.77, "lon": -122.42},
            {"id": 2, "source": "synthetic", "title": "Flood in Delhi", "magnitude": 3.2, "severity": 0.45, "occurred_ts": "2025-09-07 10:05", "lat": 28.61, "lon": 77.20},
            {"id": 3, "source": "synthetic", "title": "Wildfire near Sydney", "magnitude": 5.1, "severity": 0.81, "occurred_ts": "2025-09-07 10:10", "lat": -33.87, "lon": 151.21}
        ])

df = get_data()

# Convert objects (UUID/datetime) to strings for Streamlit compatibility
for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].astype(str)

# Show table
st.subheader("Latest Incidents")
st.dataframe(df)

# Severity over time
st.subheader("Severity Over Time")
if not df.empty:
    st.line_chart(df[["occurred_ts", "severity"]].set_index("occurred_ts"))

# Map of incidents
st.subheader("Incident Map")
if not df.empty:
    st.map(df[["lat", "lon"]])