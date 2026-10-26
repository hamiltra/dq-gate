# DQ Gate

A GitHub Actions pipeline that runs dbt tests and Snowflake data quality checks, blocks a merge or deploy when testing coverage is missing, and records evidence in a ServiceNow change request.

**Status:** M4 complete (dbt tests and Snowflake data metric functions gate every pull request). Next: M5, the coverage gate and reporting. See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full plan, milestones and timeline.

All data in this project is synthetic.

## Architecture (target)

```mermaid
flowchart LR
    PR[Pull request] --> CI[GitHub Actions pipeline]
    CI --> L[Lint + pytest]
    CI --> D[dbt build, changed models only]
    D --> SF[(Snowflake)]
    CI --> G[Coverage gate]
    CI --> SN[ServiceNow change + evidence]
    SN --> P[Deploy gate]
```

## Quick start

Requires Python 3.11+.

```bash
make setup     # venv, dev dependencies, pre-commit hooks
make check     # lint + tests (what CI runs)
```

Copy `.env.example` to `.env` for local credentials. Never commit `.env`.

## Repository layout

```
.github/workflows/   CI pipeline (pull requests and main), manual RAW reload, DMF checks
src/dq_tools/         Python tooling (config, ServiceNow client, synthetic data, RAW loader, DMFs)
tests/                pytest unit tests
dbt/                  dbt project: staging and mart models, tests, CI schema macros
snowflake/            one-off Snowflake setup SQL (grants)
scripts/              CLI entry points (data generation, RAW load, DMFs, smoke tests, dbt in Docker)
docs/                 project plan, runbooks, AI workflow log, screenshots
```

## GitHub setup checklist (M1)

1. Push `main` to GitHub (done if you can see the files).
2. Settings > Rules > Rulesets > New branch ruleset, target `main`:
   - Require a pull request before merging
   - Require status checks to pass (add `lint` and `unit-tests` after their first run)
   - Block force pushes
3. Open a pull request and confirm `lint` and `unit-tests` run under Actions.
4. Break a test on purpose, confirm the merge is blocked, then fix it (screenshot for the README).
5. Optional: register a self-hosted runner (Settings > Actions > Runners). Do not let fork pull requests run on it if the repo is public.


## Merge gate demo (M1)

`main` is protected by a branch ruleset: changes need a pull request, and the `lint` and `unit-tests` checks must pass before merging. To prove it, I broke a test on purpose (PR #2).

**Blocked:** `unit-tests` fails, so the merge button is disabled.

![Merge blocked by failing unit-tests check](docs/img/m1-blocked.png)

**Unblocked:** after reverting the change, both required checks pass and the merge is allowed.

![Merge enabled after checks pass](docs/img/m1-unblocked.png)

## ServiceNow integration (M2)

`dq_tools.servicenow.ServiceNowClient` creates a change request, adds a work note and attaches a file through the ServiceNow REST API. Unit tests mock all HTTP calls, so CI never touches a live instance. A hand-run smoke test (`python scripts/servicenow_smoke.py`) exercises the real API against a personal developer instance using a dedicated least-privilege integration user.

![Change request created by the smoke test](docs/img/m2-servicenow-change.png)

## M3: dbt pipeline gated in CI

Synthetic securities, daily prices and positions (seeded, no real data) are loaded into
Snowflake `DQ_DEMO.RAW`. A dbt project builds staging views and mart tables with 25 data
tests and 1 unit test. Every pull request runs `dbt build` against its own schemas
(`CI_PR_<n>_STAGING`, `CI_PR_<n>_MARTS`), which are dropped when the job ends. CI logs in
with key-pair auth; the private key lives only in a GitHub secret.

The gate demo: I loaded RAW with three known defects (a duplicate security, a negative price,
and an orphan position). Four tests failed, the marts were skipped, and the merge was blocked.
After reloading clean data, all 32 nodes passed.

| Defects loaded: merge blocked | Failing tests | Clean data: all checks pass |
|---|---|---|
| ![blocked](docs/img/m3-gate-blocked.png) | ![log](docs/img/m3-gate-log.png) | ![passed](docs/img/m3-gate-passed.png) |

| Defect | Test that caught it |
|---|---|
| Duplicate security | `unique_stg_securities_security_id`, `unique_stg_securities_ticker` |
| Negative price | `assert_prices_positive` |
| Orphan position | `relationships_stg_positions_security_id` |

Dependabot PRs skip `dbt-build` because GitHub does not give them Actions secrets.
Slim CI (only changed models) is still to do.

## M4: Snowflake data metric functions

Five checks run against `DQ_DEMO.RAW`: `NULL_COUNT` on `security_id` and `close_price`,
`DUPLICATE_COUNT` on `SECURITIES.security_id`, `FRESHNESS`, and a custom function,
`DQ_AUDIT.NON_POSITIVE_COUNT`, that counts zero or negative prices. The functions are attached to the
tables, so Snowflake evaluates them itself whenever the data changes. `scripts/dmf.py check` also
calls each one directly, compares the value with a limit, writes a row per check to
`DQ_AUDIT.DMF_RESULTS`, and exits non-zero on a failure. The `dmf-check` CI job runs it on every
pull request.

```bash
python scripts/dmf.py apply     # create the custom function and attach the functions (once)
python scripts/dmf.py check     # run the checks, record results, fail on a bad value
python scripts/dmf.py native    # show what Snowflake recorded for the attached functions
```

With the injected defects loaded, the duplicate security and the negative price were caught; the
orphan position is a cross-table problem that only the dbt `relationships` test catches.

| Defects loaded: two checks fail | Clean data: all pass | Results in `DQ_AUDIT` |
|---|---|---|
| ![fail](docs/img/m4-dmf-fail.png) | ![pass](docs/img/m4-dmf-pass.png) | ![audit](docs/img/m4-audit-table.png) |

Scheduled DMFs run on Snowflake-managed compute. To pause them, set `DATA_METRIC_SCHEDULE = ''`
on the RAW tables; `scripts/dmf.py apply` turns them back on.
