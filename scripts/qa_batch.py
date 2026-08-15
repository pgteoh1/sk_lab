"""Batch data-quality check for all station CSVs in data/."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
REQUIRED_COLUMNS = ["unit_id", "voltage_v", "temp_c", "result"]
VOLTAGE_MIN, VOLTAGE_MAX = 3.0, 3.6
TEMP_MIN, TEMP_MAX = 0, 60


def verdict_for(failure_rate):
    if failure_rate == 0:
        return "CLEAN"
    if failure_rate < 5:
        return "MINOR ISSUES"
    return "NEEDS REVIEW"


def analyze(csv_path: Path):
    raw_lines = csv_path.read_text().splitlines()
    # Detect a malformed leading line that isn't part of the real header/data
    header_idx = 0
    if len(raw_lines) > 1 and "," not in raw_lines[0]:
        header_idx = 1  # skip garbage first line

    from io import StringIO
    content = "\n".join(raw_lines[header_idx:])
    df = pd.read_csv(StringIO(content))

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        report_md = f"""# Data Quality Report - {csv_path.name}
Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

## Summary
| Metric | Value |
|---|---|
| Rows | {len(df)} |
| Columns | {', '.join(df.columns)} |
| Missing values | not evaluated |
| Duplicate rows | not evaluated |
| Voltage violations | not evaluated |
| Temperature violations | not evaluated |
| Failure rate | not evaluated |

## Offending units
Checks were not evaluated because required column(s) are missing: {', '.join(missing_cols)}.

## PASS/FAIL
| Result | Count |
|---|---|
| PASS | not evaluated |
| FAIL | not evaluated |

## Verdict
N/A

## Skip reason
Missing required column(s): {', '.join(missing_cols)}
"""
        return {
            "file": csv_path.name,
            "status": "skipped",
            "row_count": len(df),
            "violations": {},
            "verdict": "N/A",
            "skip_reason": f"missing required column(s): {', '.join(missing_cols)}",
        }, report_md

    n_rows = len(df)
    missing_mask = df.isna().any(axis=1)
    dup_mask = df.duplicated(keep=False)
    voltage_mask = (df["voltage_v"] < VOLTAGE_MIN) | (df["voltage_v"] > VOLTAGE_MAX)
    temp_mask = (df["temp_c"] < TEMP_MIN) | (df["temp_c"] > TEMP_MAX)

    violations = {
        "missing_values": int(missing_mask.sum()),
        "duplicate_rows": int(dup_mask.sum()),
        "voltage_violations": int(voltage_mask.sum()),
        "temp_violations": int(temp_mask.sum()),
    }
    offenders = {
        "missing_values": df.loc[missing_mask, "unit_id"].tolist(),
        "duplicate_rows": df.loc[dup_mask, "unit_id"].tolist(),
        "voltage_violations": df.loc[voltage_mask, "unit_id"].tolist(),
        "temp_violations": df.loc[temp_mask, "unit_id"].tolist(),
    }

    affected_rows = (missing_mask | dup_mask | voltage_mask | temp_mask).sum()
    failure_rate = round(100 * affected_rows / n_rows, 2) if n_rows else 0
    verdict = verdict_for(failure_rate)

    pass_count = int((df["result"] == "PASS").sum())
    fail_count = int((df["result"] == "FAIL").sum())

    report_md = f"""# Data Quality Report - {csv_path.name}
Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

## Summary
| Metric | Value |
|---|---|
| Rows | {n_rows} |
| Columns | {', '.join(df.columns)} |
| Missing values | {violations['missing_values']} |
| Duplicate rows | {violations['duplicate_rows']} |
| Voltage violations | {violations['voltage_violations']} |
| Temperature violations | {violations['temp_violations']} |
| Failure rate | {failure_rate}% |

## Offending units
- Missing values: {', '.join(offenders['missing_values']) or 'none'}
- Duplicate rows: {', '.join(offenders['duplicate_rows']) or 'none'}
- Voltage violations: {', '.join(offenders['voltage_violations']) or 'none'}
- Temperature violations: {', '.join(offenders['temp_violations']) or 'none'}

## PASS/FAIL
| Result | Count |
|---|---|
| PASS | {pass_count} |
| FAIL | {fail_count} |

## Verdict
{verdict}
"""

    result = {
        "file": csv_path.name,
        "status": "processed",
        "row_count": n_rows,
        "violations": violations,
        "verdict": verdict,
    }
    return result, report_md


def load_progress():
    progress_path = REPORTS_DIR / "progress.log"
    processed = set()
    if progress_path.exists():
        for line in progress_path.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                processed.add(parts[1])
    return processed


def log_progress(csv_name, status):
    progress_path = REPORTS_DIR / "progress.log"
    timestamp = datetime.now(timezone.utc).isoformat()
    with progress_path.open("a") as f:
        f.write(f"{timestamp} {csv_name} {status}\n")


def main():
    parser = argparse.ArgumentParser(description="Batch data-quality check for station CSVs.")
    parser.add_argument(
        "--station",
        action="append",
        metavar="NAME",
        help="Station name to process (without .csv extension). "
             "Can be repeated. If omitted, all files in data/ are processed.",
    )
    args = parser.parse_args()

    if args.station:
        files = []
        for name in args.station:
            matched = sorted(DATA_DIR.glob(f"{name}.csv"))
            if not matched:
                print(f"Warning: no file found for station '{name}' in {DATA_DIR}/", file=sys.stderr)
            files.extend(matched)
    else:
        files = sorted(DATA_DIR.glob("*.csv"))
    already_processed = load_progress()
    batch_files = []
    any_needs_review = False
    any_skipped = False
    any_minor = False

    for csv_path in files:
        if csv_path.name in already_processed:
            continue

        result, report_md = analyze(csv_path)
        batch_files.append(result)
        if result["status"] == "skipped":
            any_skipped = True
        elif result["verdict"] == "NEEDS REVIEW":
            any_needs_review = True
        elif result["verdict"] == "MINOR ISSUES":
            any_minor = True

        if report_md is not None:
            out_path = REPORTS_DIR / f"{csv_path.stem}-quality.md"
            out_path.write_text(report_md)

        log_progress(csv_path.name, result["status"])

    if any_needs_review or any_skipped:
        batch_verdict = "NEEDS REVIEW"
    elif any_minor:
        batch_verdict = "MINOR ISSUES"
    else:
        batch_verdict = "CLEAN"

    batch_result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": batch_files,
        "batch_verdict": batch_verdict,
    }

    (REPORTS_DIR / "batch-result.json").write_text(json.dumps(batch_result, indent=2))
    print(json.dumps(batch_result, indent=2))


if __name__ == "__main__":
    main()
