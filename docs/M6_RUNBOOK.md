# M6 runbook: ServiceNow change and deploy gate

What this adds:

- `src/dq_tools/servicenow.py`: `get_change` (number, state, approval), `get_change_state`, and
  `set_change_state` (state plus an optional work note and other fields)
- `src/dq_tools/change.py`: normal-change state values, the approve/reject/wait decision, the
  polling loop, and the change description
- `scripts/change_request.py`: `create`, `wait` and `finish` commands
- `.github/workflows/ci.yml`: jobs `change-request` and `deploy-prod`, which run only on pushes to `main`
- GitHub environment `production`, which only `main` can deploy to (created in repository settings)

## How a deploy works

1. A pull request merges, and the push to `main` runs every check again (`dbt-build` tests the
   merged code in `CI_MAIN_*` schemas).
2. `change-request` opens a normal change named `DQ Gate production deploy <sha>`. It attaches
   `dbt-junit.xml`, `run_results.json` and `coverage-summary.md` and adds a work note that links
   to the pipeline run.
3. `deploy-prod` (environment `production`) checks the change every 30 seconds for up to 15
   minutes:
   - **approved**, and state Scheduled or Implement: it moves the change to Implement (if it is
     Scheduled) and deploys
   - **rejected**, Canceled or Closed: it fails at once
   - **15 minutes pass** with neither: it fails with "Approve the change in ServiceNow, then re-run
     this job". Approve it, then use **Re-run failed jobs** on the run. The re-run uses the same
     change, because the change-request job's output is kept.
4. It runs `dbt build --target prod`, which writes `STAGING` and `MARTS` and runs every test
   against production.
5. It records the result in the change. On success, it adds a work note with the test counts,
   sets the actual end time and moves the change to **Review**. On failure, it adds a work note
   and leaves the state alone. Closing the change after review is done by hand in ServiceNow.

A new merge never cancels a deploy that is waiting or running: runs on `main` queue instead.

## Approving a change (personal developer instance)

These are the steps that worked on our instance on Oct 27, 2026, with `CHG0030002`.

1. Open the change in the classic form:
   `https://<instance>.service-now.com/change_request.do?sys_id=<sys_id>`. The `deploy-prod`
   log shows the number, and the `change-request` log shows the `sys_id`. A workspace view may
   not show the Approvers related list.
2. Click **Request Approval**. The change moves to **Assess**, gets the **Application
   Development** assignment group, and requests approval from each of its members.
3. In the **Schedule** tab, set the **Planned start** and **Planned end** dates, then save.
4. Open the approval records:
   `https://<instance>.service-now.com/sysapproval_approver_list.do?sysparm_query=sysapproval=<sys_id>`
   Right-click a **Requested** row, choose **Approve** (or open it, set State to Approved and
   click Update). The change moves to **Authorize**.
5. Reload the approval list and approve one of the new CAB rows the same way. The change moves
   to **Scheduled** with approval **Approved**, and within 30 seconds the pipeline moves it to
   **Implement** and starts the deploy.

## Things learned on the live instance

- The integration user cannot read `sys_choice`, so the state values are constants in
  `dq_tools.change` (the stock normal-change values: New -5, Assess -4, Authorize -3, Scheduled -2,
  Implement -1, Review 0, Closed 3, Canceled 4).
- The state model goes Scheduled -> Implement -> Review. ServiceNow sets the actual start when a
  change enters Implement.
- Moving to Review is blocked by the business rule **Actual Start/End Date Validation** when the
  actual end is earlier than the actual start. `finish` therefore sets the actual end
  (`work_end`) to the current time, in UTC (the Table API reads raw date values as UTC).

## Running the commands by hand

With `.env` filled in:

```bash
python scripts/change_request.py create --sha "$(git rev-parse HEAD)" --run-url "manual test" \
    --attach dbt-junit.xml
python scripts/change_request.py wait --sys-id <sys_id> --timeout 900 --interval 30
python scripts/change_request.py finish --sys-id <sys_id> --result success --run-url "manual test"
```
