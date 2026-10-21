# dbt project (milestone M3)

dbt Core project `dq_gate` on Snowflake. All data is synthetic.

```
dbt/
  profiles.yml        Snowflake profile; reads everything from env vars (no secrets inside)
  requirements.txt    Pinned toolchain (dbt-core, dbt-snowflake)
  Dockerfile          Image with that toolchain: docker build -t dq-gate-dbt -f dbt/Dockerfile .
  dq_gate/
    dbt_project.yml
    models/staging/   views over RAW: stg_securities, stg_daily_prices, stg_positions (+ source freshness)
    models/marts/     tables: dim_security, fct_position_valuation, mart_portfolio_summary (+ 1 unit test)
    macros/           generate_schema_name (isolated schemas), drop_ci_schemas (CI cleanup)
    tests/            singular tests; tests/generic/unique_combination
```

## Targets

| Target | Schemas written | Used by |
|---|---|---|
| `dev` | `DBT_DEV_STAGING`, `DBT_DEV_MARTS` | local runs |
| `ci` | `CI_PR_<n>_STAGING`, `CI_PR_<n>_MARTS` (dropped when the job ends) | GitHub Actions |
| `prod` | `STAGING`, `MARTS` | deploy job (M6) |

Source data lives in `DQ_DEMO.RAW` and is loaded by `scripts/load_raw.py`
(or the manual *Load RAW data* workflow).

## Running dbt

Locally, through Docker (reads the `SNOWFLAKE_*` values from `.env`, mounts the key read-only):

```bash
scripts/dbt-docker.sh source freshness --target dev
scripts/dbt-docker.sh build --target dev
```

In CI the `dbt-build` job runs the same commands with `--target ci`.

## What is tested

- Generic tests: `unique`, `not_null`, `accepted_values`, `relationships`, and a custom
  `unique_combination` test.
- Singular tests: prices are positive, every position has a price on its date, and the
  portfolio summary reconciles to the position-level fact.
- One dbt unit test: market value equals quantity times closing price.
- Source freshness: warn after 7 days, error after 30 days.

When a test fails, dbt skips everything downstream of it, so bad data never reaches the marts.
