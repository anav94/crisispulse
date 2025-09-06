# scripts/run_drift_check.py
print("RUN_DRIFT_CHECK v4")  # sanity marker

import os
import pandas as pd
from evidently import Report, Dataset, DataDefinition
from evidently.presets import DataDriftPreset
from evidently.metrics import DriftedColumnsCount  # returns count+share directly

def extract_drift_share(snapshot_dict: dict):
    """Find drift share robustly from the snapshot dict."""
    # Prefer DriftedColumnsCount metric (returns {"count": int, "share": float})
    for m in snapshot_dict.get("metrics", []):
        if isinstance(m, dict):
            v = m.get("value")
            if isinstance(v, dict) and "share" in v and "count" in v:
                try:
                    return float(v["share"])
                except Exception:
                    pass
    # Fallback: deep search for any key that looks like share_of_drift*
    def deep(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and "drift" in k.lower() and "share" in k.lower():
                    try:
                        fv = float(v)
                        if 0.0 <= fv <= 1.0:
                            return fv
                    except Exception:
                        pass
                got = deep(v)
                if got is not None:
                    return got
        elif isinstance(o, list):
            for it in o:
                got = deep(it)
                if got is not None:
                    return got
        return None
    return deep(snapshot_dict)

def main():
    # 1) load dataset
    df = pd.read_csv("notebooks/telco.csv")

    # coerce types (TotalCharges often loads as text in this CSV)
    if "TotalCharges" in df.columns:
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")

    # 2) split: reference (80%) vs current (20%)
    reference_df = df.sample(frac=0.8, random_state=42).reset_index(drop=True)
    current_df   = df.drop(reference_df.index).reset_index(drop=True)

    # 3) define column mapping via new DataDefinition
    cat_cols = ["gender","Partner","Dependents","PhoneService","MultipleLines",
                "InternetService","OnlineSecurity","OnlineBackup","DeviceProtection",
                "TechSupport","StreamingTV","StreamingMovies","Contract",
                "PaperlessBilling","PaymentMethod","Churn"]
    num_cols = ["tenure","MonthlyCharges","TotalCharges","SeniorCitizen"]

    definition = DataDefinition(
        id_column="customerID",
        numerical_columns=[c for c in num_cols if c in df.columns],
        categorical_columns=[c for c in cat_cols if c in df.columns],
    )

    # 4) build Dataset objects (new 0.7 flow)
    current_data   = Dataset.from_pandas(current_df, data_definition=definition)
    reference_data = Dataset.from_pandas(reference_df, data_definition=definition)

    # 5) run report with a preset + an explicit dataset-level drift metric
    report = Report([DataDriftPreset(), DriftedColumnsCount()])
    snapshot = report.run(current_data=current_data, reference_data=reference_data)

    # 6) save outputs
    os.makedirs("artifacts/evidently", exist_ok=True)
    html_path = "artifacts/evidently/drift_report.html"
    json_path = "artifacts/evidently/drift_report.json"
    snapshot.save_html(html_path)
    snapshot.save_json(json_path)
    print(f"✅ Drift report saved to {html_path}")
    print(f"✅ Drift JSON saved to {json_path}")

    # 7) extract drift share and alert
    out = snapshot.dict()
    drift_share = extract_drift_share(out)

    if drift_share is None:
        # help debug if the schema changes again
        metric_ids = []
        for m in out.get("metrics", []):
            if isinstance(m, dict):
                metric_ids.append(m.get("metric") or m.get("metric_id") or m.get("id"))
            else:
                metric_ids.append(type(m).__name__)
        print("⚠️ Could not find drift share. Metrics present:", metric_ids)
        return

    if drift_share > 0.20:
        print(f"⚠️ ALERT: High drift detected ({drift_share:.2%} of columns).")
    else:
        print(f"ℹ️ Drift OK ({drift_share:.2%} drifted).")

if __name__ == "__main__":
    main()
