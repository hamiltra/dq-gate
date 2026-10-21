# M3 runbook: Snowflake and dbt in CI

Follow in order. Stop and send the error text if any step does not give the expected result.

## 1. Apply the files

```bash
git switch main && git pull
git switch -c m3-dbt-pipeline
unzip -o ~/Downloads/m3-dbt-pipeline.zip      # run from the repo root; paths are inside the zip
git status --short
```

Expect new and changed files under `.github/workflows/`, `dbt/`, `scripts/`, `src/dq_tools/`,
`tests/`, plus `Makefile`, `pyproject.toml`, `.env.example` and `docs/M3_RUNBOOK.md`.

## 2. Fix `.gitignore`

The old file ignored every `profiles.yml`, which would hide the dbt profile (it holds no secrets,
only env var names). Run:

```bash
sed -i '/^profiles.yml$/d' .gitignore
cat >> .gitignore <<'EOT'

# Synthetic data and dbt build output
data/
dbt/**/target/
dbt/**/logs/
dbt/**/dbt_packages/
dbt/**/.user.yml
EOT
git check-ignore -v dbt/profiles.yml || echo "profiles.yml is tracked: good"
```

## 3. Local checks

```bash
source .venv/bin/activate
pip install -e ".[dev,snowflake]"
make check                  # expect: 28 tests pass
```

## 4. Load the synthetic data into Snowflake RAW

```bash
make load-raw
```

Expect `RAW.SECURITIES: 40 rows`, `RAW.DAILY_PRICES: 2200 rows`, `RAW.POSITIONS: 3300 rows`.
Check in a Snowsight worksheet:

```sql
USE ROLE ACCOUNTADMIN;
SELECT COUNT(*) FROM DQ_DEMO.RAW.SECURITIES;
```

## 5. Run dbt locally in Docker

```bash
scripts/dbt-docker.sh --version
scripts/dbt-docker.sh source freshness --target dev
scripts/dbt-docker.sh build --target dev        # expect PASS=32, ERROR=0
```

Then remove the dev schemas it created:

```sql
DROP SCHEMA IF EXISTS DQ_DEMO.DBT_DEV_STAGING CASCADE;
DROP SCHEMA IF EXISTS DQ_DEMO.DBT_DEV_MARTS CASCADE;
```

## 6. Open the pull request

```bash
git add -A
git status --short          # nothing from data/, no .env, no key files
git commit -m "M3: synthetic data, dbt project and dbt-build CI job"
git push -u origin HEAD
```

The PR should show three checks: `lint`, `unit-tests`, `dbt-build`. The `dbt-build` job writes the
`SNOWFLAKE_PRIVATE_KEY` secret to a temporary file, builds into `CI_PR_<n>_*` schemas, uploads
`run_results.json` and `manifest.json`, then drops those schemas.

After `dbt-build` has passed once, add it to the ruleset (Settings > Rules > Rulesets > edit the
`main` ruleset > required status checks > add `dbt-build`).

## 7. Demonstrate the gate failing (screenshots for the README)

1. Actions tab > **Load RAW data** > Run workflow > tick `inject_defects`.
2. Push a small change (or re-run the PR's checks): `dbt-build` fails on 4 tests (negative price,
   orphan position, duplicate security ID and ticker) and everything downstream is skipped.
   Screenshot the failed job.
3. Run **Load RAW data** again with `inject_defects` off, re-run the checks, and screenshot the green run.

Note RAW is shared, so while defects are loaded every pull request's `dbt-build` will fail.

## 8. Tick the plan

When all of the above works, tick the M3 boxes in `docs/PROJECT_PLAN.md` except the slim-CI line
(changed models only), which is the next piece.

## What was and was not verified before you received this

Verified in the build environment: lint and 28 unit tests; the full dbt build (32 checks) on a local
DuckDB; the gate failing on injected defects; the CI cleanup macro; the Snowflake profile parsing for
all three targets; the `.env` handling in `dbt-docker.sh` using a stand-in `docker` command.

Not verified (no Snowflake access or Docker daemon there), so expect to debug these first:
the `PUT`/`COPY INTO` loader against real Snowflake, dbt key-pair login, SQL dialect differences
on Snowflake, the Docker image build, and the GitHub workflows' first run.
