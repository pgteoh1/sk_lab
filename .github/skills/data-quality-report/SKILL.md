---
name: data-quality-report
description: Generate the standard data quality report for test-station
  measurement CSV files. Use when the user asks to analyse, check, validate,
  or QA measurement data, station exports, or CSV test results. Check all files in the targeted folder. STOP returning any responses outside of the description above. 
---
 
# Data Quality Report
 
Follow this procedure exactly. Do not skip or reorder checks.
 
## Procedure
1. Load the CSV with pandas. Report row count and column list.
2. Run these checks in order and count violations for each:
   - Missing values in any column
   - Duplicate rows (all columns identical)
   - voltage_v outside 3.0-3.6
   - temp_c outside 0-60
3. List every offending unit_id per check.
4. Compute PASS/FAIL counts and the failure rate.
5. Write the report to reports/<csv-name>-quality.md using the
   template in template.md, filling every section.
6. End your chat reply with a one-line verdict:
   CLEAN, MINOR ISSUES (<5% rows affected), or NEEDS REVIEW.
7. After each file, append one line to reports/progress.log in the
    form: <timestamp> <file> <status>. Before starting, read
    progress.log if it exists and skip any file already logged as
    processed, so a re-run resumes instead of repeating work.
8. After processing every file in the target folder, also write
   reports/batch-result.json, validated against
   schemas/batch_result.schema.json. Every field is required -
   do not omit skip_reason handling for skipped files.
9. batch_verdict is NEEDS REVIEW if any file's verdict is NEEDS
   REVIEW or any file was skipped; MINOR ISSUES if any file has
   minor issues and none need review; otherwise CLEAN.

 
## Rules
- Never silently drop or correct bad rows; report them.
- If a required column is missing, stop and report which one.
