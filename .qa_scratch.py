import pandas as pd
import json

REQUIRED_COLS = ["timestamp", "station", "unit_id", "voltage_v", "current_a", "temp_c", "result"]
files = ["station_A", "station_B", "station_C"]

for f in files:
    print("=====", f, "=====")
    path = f"data/{f}.csv"
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print("PARSE ERROR:", repr(e))
        continue
    print("columns:", df.columns.tolist())
    print("rows:", len(df))
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    print("missing_cols:", missing_cols)
    if not missing_cols:
        print(df.to_string())
