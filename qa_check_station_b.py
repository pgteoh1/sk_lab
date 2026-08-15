#!/usr/bin/env python3
"""QA check for station_B.csv - produces only batch-result.json"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import os

# Change to workspace directory
os.chdir(Path(__file__).parent)

# Define paths
data_file = Path("data/station_B.csv")
output_file = Path("reports/batch-result.json")

# Required columns
REQUIRED_COLUMNS = {"timestamp", "station", "unit_id", "voltage_v", "current_a", "temp_c", "result"}

# Limits
VOLTAGE_MIN, VOLTAGE_MAX = 3.0, 3.6
TEMP_MIN, TEMP_MAX = 0, 60

def check_file(filepath):
    """Run QA checks on a CSV file."""
    filename = filepath.name
    violations = {
        "missing_values": [],
        "duplicate_rows": [],
        "voltage_out_of_range": [],
        "temperature_out_of_range": []
    }
    
    try:
        # Load CSV - skip first line if it contains the filename
        df = pd.read_csv(filepath)
        
        # Check if first row contains the filename as a column name (data quality issue)
        if df.columns[0] == "data/station_B.csv":
            # Re-read skipping the first row
            df = pd.read_csv(filepath, skiprows=1)
        
        row_count = len(df)
        
        # Check required columns
        missing_cols = REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            return {
                "file": filename,
                "status": "skipped",
                "row_count": 0,
                "violations": violations,
                "verdict": "N/A",
                "skip_reason": f"Missing required columns: {', '.join(sorted(missing_cols))}"
            }
        
        # Check 1: Missing values
        for col in df.columns:
            missing_mask = df[col].isna()
            if missing_mask.any():
                unit_ids = df.loc[missing_mask, "unit_id"].unique().tolist()
                violations["missing_values"].extend(unit_ids)
        violations["missing_values"] = list(set(violations["missing_values"]))  # deduplicate
        
        # Check 2: Duplicate rows
        dup_mask = df.duplicated(keep=False)
        if dup_mask.any():
            dup_unit_ids = df.loc[dup_mask, "unit_id"].unique().tolist()
            violations["duplicate_rows"] = dup_unit_ids
        
        # Check 3: Voltage out of range
        voltage_mask = (df["voltage_v"] < VOLTAGE_MIN) | (df["voltage_v"] > VOLTAGE_MAX)
        if voltage_mask.any():
            violations["voltage_out_of_range"] = df.loc[voltage_mask, "unit_id"].unique().tolist()
        
        # Check 4: Temperature out of range
        temp_mask = (df["temp_c"] < TEMP_MIN) | (df["temp_c"] > TEMP_MAX)
        if temp_mask.any():
            violations["temperature_out_of_range"] = df.loc[temp_mask, "unit_id"].unique().tolist()
        
        # Calculate violation counts and rows affected
        total_violations = sum(len(v) for v in violations.values())
        
        # Determine verdict
        if total_violations == 0:
            verdict = "CLEAN"
        else:
            failure_rate = (total_violations / row_count) * 100 if row_count > 0 else 0
            if failure_rate < 5:
                verdict = "MINOR ISSUES"
            else:
                verdict = "NEEDS REVIEW"
        
        return {
            "file": filename,
            "status": "processed",
            "row_count": row_count,
            "violations": violations,
            "verdict": verdict
        }
    
    except Exception as e:
        return {
            "file": filename,
            "status": "skipped",
            "row_count": 0,
            "violations": violations,
            "verdict": "N/A",
            "skip_reason": str(e)
        }

# Run check on station_B.csv
result = check_file(data_file)

# Determine batch verdict
batch_verdict = result["verdict"]
if result["status"] == "skipped":
    batch_verdict = "NEEDS REVIEW"

# Create batch result
batch_result = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "files": [result],
    "batch_verdict": batch_verdict
}

# Write batch-result.json
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, "w") as f:
    json.dump(batch_result, f, indent=2)

print(json.dumps(batch_result, indent=2))
print(f"\nBatch result written to {output_file}")
