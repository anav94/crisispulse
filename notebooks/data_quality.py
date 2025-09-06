import pandas as pd
import clickhouse_connect
from evidently.report import Report
from evidently.metrics import ColumnDriftMetric, DatasetDriftMetric

# connect to ClickHouse
client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="default",
    password="cp_pass",
    database="crisispulse"
)

# grab last 500 incidents
df = client.query_df("""
    SELECT occurred_ts, source, magnitude, severity
    FROM crisispulse.incidents
    ORDER BY occurred_ts DESC
    LIMIT 500
""")

# build drift report
report = Report(metrics=[
    ColumnDriftMetric(column_name="magnitude"),
    ColumnDriftMetric(column_name="severity"),
    DatasetDriftMetric()
])

report.run(reference_data=df.tail(250), current_data=df.head(250))
report.save_html("docs/evidently_report.html")
print("✅ Report generated at docs/evidently_report.html")