# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DQ Gate: a GitHub Actions pipeline that runs dbt tests and Snowflake data quality checks on **synthetic** financial data (securities, daily prices, positions), blocks merges/deploys when checks or test coverage fail, and records evidence in a ServiceNow change request. It is built milestone by milestone (M0–M7); `docs/PROJECT_PLAN.md` holds the milestone checklists and is ticked off as work lands. M1–M5 are done (M5's README screenshots are still to add). Still to do: slim CI (M3 leftover) and the ServiceNow deploy gate (M6).

Constraints from the plan: synthetic data only, and no real data, code or designs from current or former employers. CI runs on GitHub Actions, not GitLab (the job description in `docs/HANDOFF.md` says GitLab, but that was a deliberate choice).

## Commands

```bash
make setup        # .venv, pip install -e ".[dev,snowflake]", pre-commit install
make check        # lint + test, same as the CI lint/unit-tests jobs
make lint         # ruff check . && ruff format --check .
make format       # ruff --fix + ruff format
make test         # pytest --cov
.venv/bin/pytest tests/test_load.py::test_create_table_sql_has_loaded_at_default   # single test

make data                       # synthetic CSVs -> data/synthetic (gitignored)
make data ARGS=--inject-defects # adds the 3 known defects used for gate demos
make load-raw                   # generate + load into Snowflake DQ_DEMO.RAW (needs .env)

scripts/dbt-docker.sh build --target dev             # dbt in the pinned Docker image
scripts/dbt-docker.sh source freshness --target dev

python scripts/coverage_gate.py --base origin/main     # needs dbt/dq_gate/target/manifest.json (dbt parse)
python scripts/results_to_junit.py                    # target/run_results.json -> dbt-junit.xml
```

Python 3.11+, ruff with line length 100 and rules `E,F,I,UP,B,SIM`. Credentials come from `.env` (see `.env.example`): ServiceNow basic auth plus Snowflake key-pair auth (`SNOWFLAKE_PRIVATE_KEY_PATH`). Snowflake has no password auth.

## Architecture

**Python package `src/dq_tools/`** (installed editable as `dq-tools`). Thin CLI wrappers live in `scripts/` and call into it:
- `config.py`: frozen `*Settings.from_env(env=None)` dataclasses. They take an optional mapping so tests can pass a dict instead of patching `os.environ`, and raise `ConfigError` listing every missing var.
- `servicenow.py`: `ServiceNowClient` (create change, work note, attach file, read state) over the REST API with `requests`. Tests mock HTTP with `responses`, so CI never calls a live instance. `scripts/servicenow_smoke.py` is the hand-run live check.
- `synthetic.py`: seeded (`DEFAULT_SEED`) data generator. `inject_known_defects` adds a duplicate security, a negative price and an orphan position, which the dbt tests and DMFs must catch.
- `load.py`: builds SQL strings (CREATE / TRUNCATE / PUT to the table stage / COPY INTO with explicit casts) and runs them on any DB-API connection. Tests use a fake cursor that records SQL. `RAW_TABLES` is the single schema definition for RAW.
- `warehouse.py`: imports `snowflake.connector` lazily so unit tests and the CI `unit-tests` job run without the `snowflake` extra. Keep Snowflake imports lazy.
- `coverage.py`: the M5 gate, working on a parsed `manifest.json` plus a list of changed paths. A model counts as changed when its SQL file **or its properties YAML** is in the diff. It is covered when at least one data test is attached to it (`attached_node`) or a singular test refs it. A relationships test only counts for the model it is attached to, not the one it points at. Unit tests are reported but don't count on their own. `junit.py` converts `run_results.json` into one JUnit suite per resource type.

**dbt project `dbt/dq_gate/`**: source `RAW` -> staging views -> mart tables, plus generic, singular, custom generic (`unique_combination`) and unit tests, and source freshness. `dbt/profiles.yml` reads everything from env vars. dbt is pinned in `dbt/requirements.txt` and the Docker image; it is not in `pyproject.toml`.
- `macros/generate_schema_name.sql`: the `prod` target writes `STAGING`/`MARTS` as named. Every other target writes `<target.schema>_<custom>`, so CI gets `CI_PR_<n>_STAGING`/`_MARTS` (from `DBT_SCHEMA`) and dev gets `DBT_DEV_*`.
- `macros/drop_ci_schemas.sql`: CI cleanup. It refuses to run on any target but `ci`.

**CI (`.github/workflows/ci.yml`)**: the `protect-main` ruleset requires `lint`, `unit-tests`, `dbt-build` and `coverage-gate`. `dbt-build` writes the private key from a secret to `$RUNNER_TEMP`, runs `dbt source freshness` and `dbt build --target ci`, publishes the results as JUnit (the "dbt results" check, via `mikepenz/action-junit-report`), uploads the artifacts, and always drops the PR schemas. It skips Dependabot and fork PRs because they get no secrets. `coverage-gate` needs no secrets: it runs `dbt parse` with dummy `SNOWFLAKE_*` values (parse never connects), diffs against the PR base (hence `fetch-depth: 0`), and updates a single PR comment found by its `<!-- dq-gate:coverage-gate -->` marker. `load-raw.yml` is a manual-only workflow that reloads the **shared** RAW tables. With `inject_defects` ticked, those tables stay broken for every PR until clean data is reloaded.

## Gotchas

- `scripts/dmf.py apply|check|native` (M4): `apply` creates the custom DMF `DQ_AUDIT.NON_POSITIVE_COUNT` and attaches the system DMFs to the RAW tables; `check` runs each one, writes `DQ_AUDIT.DMF_RESULTS` and exits non-zero on a failure. The `dmf-check` workflow runs `check` on every PR. Attached DMFs run on Snowflake-managed compute, so they cost credits even when nobody is running CI.
- Each milestone usually ends with a docs PR that adds a README section with screenshots in `docs/img/` and ticks the boxes in `docs/PROJECT_PLAN.md`. Record AI-tool usage in `docs/AI_WORKFLOW.md`.
