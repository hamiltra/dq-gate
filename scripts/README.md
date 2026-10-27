# scripts

Thin command-line wrappers around `src/dq_tools`:

- `generate_data.py`: synthetic security master, prices and positions (M3)
- `load_raw.py`: load the synthetic CSVs into Snowflake `RAW` (M3)
- `dbt-docker.sh`: run dbt in the pinned Docker image against Snowflake (M3)
- `dmf.py`: attach and run Snowflake data metric functions (M4)
- `coverage_gate.py`: fail if a changed dbt model has no data tests (M5)
- `results_to_junit.py`: convert dbt `run_results.json` to JUnit XML (M5)
- `change_request.py`: open the ServiceNow change, wait for approval, record the deploy (M6)
- `servicenow_smoke.py`, `snowflake_smoke.py`: hand-run checks against the live services
