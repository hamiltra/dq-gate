"""ServiceNow change control for the production deploy.

python scripts/change_request.py create --sha <commit> --run-url <url> \
    --run-results dbt-junit/run_results.json --coverage-summary coverage-summary.md \
    --attach dbt-junit.xml run_results.json coverage-summary.md
python scripts/change_request.py wait --sys-id <id> [--timeout 900] [--interval 30]
python scripts/change_request.py finish --sys-id <id> --result success|failure --run-url <url> \
    [--run-results dbt/dq_gate/target/run_results.json]

create prints the change number and writes sys_id/number to $GITHUB_OUTPUT when it is set.
wait exits 0 once the change is approved and Scheduled or Implement (moving it to Implement),
1 if it is rejected, canceled or the timeout passes. finish records the deploy result and, on
success, moves the change to Review. Credentials come from SERVICENOW_* (or .env locally).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from dq_tools import change
from dq_tools.config import ServiceNowSettings
from dq_tools.servicenow import ServiceNowClient


def _write_outputs(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")


def create(client: ServiceNowClient, args: argparse.Namespace) -> int:
    coverage = Path(args.coverage_summary).read_text() if args.coverage_summary else ""
    tests = ""
    if args.run_results:
        tests = change.results_summary(json.loads(Path(args.run_results).read_text()))
    record = client.create_change_request(
        f"DQ Gate production deploy {args.sha[:12]}",
        change.change_description(args.sha, args.run_url, coverage, tests),
    )
    sys_id, number = record["sys_id"], record["number"]
    print(f"Created {number} (sys_id={sys_id})")
    for path in args.attach:
        if Path(path).exists():
            client.attach_file(sys_id, path)
            print(f"Attached {Path(path).name}")
        else:
            print(f"Skipped missing {path}")
    client.add_work_note(sys_id, f"Opened by the pipeline: {args.run_url}")
    _write_outputs(sys_id=sys_id, number=number)
    return 0


def wait(client: ServiceNowClient, args: argparse.Namespace) -> int:
    result = change.wait_for_approval(client, args.sys_id, args.timeout, args.interval)
    print(
        f"{result.number}: {result.outcome} after {result.waited_seconds:.0f}s "
        f"(state={result.state_label}, approval={result.approval})"
    )
    if result.outcome == change.TIMED_OUT:
        print("Approve the change in ServiceNow, then re-run this job.")
    if result.outcome != change.APPROVED:
        return 1
    if result.state == change.SCHEDULED:
        # The state model goes Scheduled -> Implement -> Review; the deploy is the Implement step
        client.set_change_state(args.sys_id, change.IMPLEMENT, note="Production deploy started")
        print(f"{result.number}: moved to Implement")
    return 0


def finish(client: ServiceNowClient, args: argparse.Namespace) -> int:
    detail = ""
    if args.run_results and Path(args.run_results).exists():
        summary = change.results_summary(json.loads(Path(args.run_results).read_text()))
        detail = f"\ndbt build --target prod: {summary}"
    if args.result == "success":
        # ServiceNow sets the actual start on Implement; Review needs an actual end after it
        client.set_change_state(
            args.sys_id,
            change.REVIEW,
            note=f"Deployed to production: {args.run_url}{detail}",
            fields={"work_end": change.servicenow_utc()},
        )
        print("Recorded the deploy and moved the change to Review")
    else:
        client.add_work_note(args.sys_id, f"Production deploy FAILED: {args.run_url}{detail}")
        print("Recorded the failed deploy")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create")
    p.add_argument("--sha", required=True)
    p.add_argument("--run-url", required=True)
    p.add_argument("--run-results")
    p.add_argument("--coverage-summary")
    p.add_argument("--attach", nargs="*", default=[])

    p = sub.add_parser("wait")
    p.add_argument("--sys-id", required=True)
    p.add_argument("--timeout", type=float, default=15 * 60)
    p.add_argument("--interval", type=float, default=30)

    p = sub.add_parser("finish")
    p.add_argument("--sys-id", required=True)
    p.add_argument("--result", choices=["success", "failure"], required=True)
    p.add_argument("--run-url", required=True)
    p.add_argument("--run-results", help="prod run_results.json, summarised in the work note")

    args = parser.parse_args()
    load_dotenv()
    client = ServiceNowClient.from_settings(ServiceNowSettings.from_env())
    return {"create": create, "wait": wait, "finish": finish}[args.command](client, args)


if __name__ == "__main__":
    sys.exit(main())
