# M4 runbook: Snowflake data metric functions

What this adds:

- `src/dq_tools/dmf.py`: the checks (three system DMFs, one custom DMF), SQL builders, apply and run
- `scripts/dmf.py`: `apply`, `check` and `native` commands
- `snowflake/m4_grants.sql`: the one-time grants (run by you as ACCOUNTADMIN)
- `.github/workflows/dmf-check.yml`: CI job `dmf-check` (fails the pull request on a bad value)
- `tests/test_dmf.py`: 11 unit tests (39 in total)

| Check | Table.column | Passes when |
|---|---|---|
| `NULL_COUNT` | DAILY_PRICES.security_id | 0 |
| `NULL_COUNT` | DAILY_PRICES.close_price | 0 |
| `DUPLICATE_COUNT` | SECURITIES.security_id | 0 |
| `FRESHNESS` | DAILY_PRICES.loaded_at | at most 30 days (2,592,000 s) since the last load |
| custom `DQ_AUDIT.NON_POSITIVE_COUNT` | DAILY_PRICES.close_price | 0 |

## What was and was not verified

Verified here: lint, 39 unit tests (the SQL statements and the pass/fail logic, using a fake
connection), and the workflow YAML parses. **Not verified: any statement against a real Snowflake
account.** The syntax comes from Snowflake's documentation. If a step fails, send me the error text.
The riskiest pieces are the custom DMF's ad hoc call (step 4) and the "already attached" handling.

## Step 1: branch and files

```bash
git switch main && git pull
git switch -c m4-dmfs
unzip -o ~/Downloads/m4-dmfs.zip
git status --short        # 6 new files, nothing modified
make check                # expect 39 passed
```

## Step 2: grants (Snowsight)

Open `snowflake/m4_grants.sql` in a Snowsight worksheet and use **Run All**. Check that the final
`SHOW GRANTS` lists `EXECUTE DATA METRIC FUNCTION` and the monitoring viewer role for `DQ_CI_ROLE`.
(Earlier I mentioned a `DATA_METRIC_USER` role. The current docs do not require it, because every
role can already use the system functions.)

## Step 3: attach the functions

```bash
source .venv/bin/activate
python scripts/dmf.py apply
```

Expect one line per statement, each `[ok]` (or `[already attached]` on a second run). This creates
`DQ_AUDIT.NON_POSITIVE_COUNT`, sets `DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES'` on the two RAW
tables and attaches the five functions.

## Step 4: run the checks

```bash
python scripts/dmf.py check
```

RAW should be clean, so expect five `PASS` rows and `5 passed, 0 failed`. Then look at the audit
table in a worksheet:

```sql
SELECT * FROM DQ_DEMO.DQ_AUDIT.DMF_RESULTS ORDER BY run_ts DESC;
```

## Step 5: Snowflake's own results

The attached functions are evaluated by Snowflake when the data changes. A reload counts as a
change, so run `make load-raw`, wait 5 to 10 minutes, then:

```bash
python scripts/dmf.py native
```

You should see rows with measurement time, table, metric and value. Until the first evaluation
happens the output is empty, which is normal.

## Step 6: demo the gate

1. Actions, **Load RAW data**, run with `inject_defects` checked.
2. `python scripts/dmf.py check`. Expect `FAIL` for the duplicate count (SECURITIES.security_id)
   and `NON_POSITIVE_COUNT` (1, the negative price). The null counts still pass. The orphan position
   is a cross-table problem that only the dbt `relationships` test catches. That contrast is a good
   interview point.
3. Screenshot the output as `docs/img/m4-dmf-fail.png`.
4. Reload clean data (Load RAW data, `inject_defects` unchecked), run `check` again, screenshot the
   five passes as `docs/img/m4-dmf-pass.png`.

## Step 7: commit and PR

```bash
git add src scripts tests snowflake docs .github
git status --short
git commit -m "M4: Snowflake data metric functions, audit table and dmf-check CI job"
git push -u origin m4-dmfs
gh pr create --base main --fill
```

The PR gets a new check called `dmf-check`. When it is green, add `dmf-check` to the ruleset's
required checks. Tick the M4 boxes in `docs/PROJECT_PLAN.md` once steps 4 to 6 work.

## Cost note

DMFs on a schedule run on Snowflake-managed (serverless) compute, which the `DQ_MONITOR` resource
monitor does not cap. These tables are tiny and the schedule only fires on data changes, so the
cost should be a small fraction of a credit. After the demo you can pause all scheduled evaluation:

```sql
ALTER TABLE DQ_DEMO.RAW.DAILY_PRICES SET DATA_METRIC_SCHEDULE = '';
ALTER TABLE DQ_DEMO.RAW.SECURITIES SET DATA_METRIC_SCHEDULE = '';
```

and re-enable it by running `python scripts/dmf.py apply` again. Check usage in Snowsight under
Admin, Cost management.

## If something fails

- `Insufficient privileges` on apply: step 2 was not run, or run without ACCOUNTADMIN.
- Error on the custom function call in `check`: send me the exact message. The call form for
  custom DMFs is the part I am least sure of.
- A pass of `check` before any `apply` still works for the system functions, so you can test them
  first.
