"""ServiceNow change control for production deploys (M6).

The pipeline opens a normal change for each push to main, attaches the test evidence, and the
deploy job waits here until the change is approved and scheduled. A person approves it in
ServiceNow; nothing in the pipeline can approve its own change.

The decision logic is a pure function and the wait loop takes its clock and sleep as arguments,
so both are unit-tested without a ServiceNow instance or real waiting.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from dq_tools.servicenow import ServiceNowClient

# Normal change states (change_request.state values on a stock instance)
NEW = "-5"
ASSESS = "-4"
AUTHORIZE = "-3"
SCHEDULED = "-2"
IMPLEMENT = "-1"
REVIEW = "0"
CLOSED = "3"
CANCELED = "4"

STATE_LABELS = {
    NEW: "New",
    ASSESS: "Assess",
    AUTHORIZE: "Authorize",
    SCHEDULED: "Scheduled",
    IMPLEMENT: "Implement",
    REVIEW: "Review",
    CLOSED: "Closed",
    CANCELED: "Canceled",
}

# A change is ready to deploy once it is approved and has reached one of these states
DEPLOYABLE_STATES = {SCHEDULED, IMPLEMENT}

APPROVED = "approved"
REJECTED = "rejected"
WAITING = "waiting"
TIMED_OUT = "timed out"


def decide(state: str, approval: str) -> str:
    """Return APPROVED, REJECTED or WAITING for a change's raw state and approval values."""
    if approval == "rejected" or state in {CANCELED, CLOSED}:
        return REJECTED
    if approval == "approved" and state in DEPLOYABLE_STATES:
        return APPROVED
    return WAITING


@dataclass(frozen=True)
class GateResult:
    outcome: str
    number: str
    state: str
    approval: str
    waited_seconds: float

    @property
    def state_label(self) -> str:
        return STATE_LABELS.get(self.state, self.state)


def wait_for_approval(
    client: ServiceNowClient,
    sys_id: str,
    timeout: float = 15 * 60,
    interval: float = 30,
    log: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> GateResult:
    """Poll the change until it is approved, rejected or ``timeout`` seconds have passed."""
    start = clock()
    last_seen = None
    while True:
        change = client.get_change(sys_id)
        state, approval = change["state"], change["approval"]
        outcome = decide(state, approval)
        waited = clock() - start
        if (state, approval) != last_seen:
            log(f"{change['number']}: state={STATE_LABELS.get(state, state)} approval={approval}")
            last_seen = (state, approval)
        if outcome != WAITING:
            return GateResult(outcome, change["number"], state, approval, waited)
        if waited + interval > timeout:
            return GateResult(TIMED_OUT, change["number"], state, approval, waited)
        sleep(interval)


def servicenow_utc(moment: datetime | None = None) -> str:
    """A date-time as the Table API's raw value: UTC, 'YYYY-MM-DD HH:MM:SS'."""
    return (moment or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def results_summary(run_results: dict) -> str:
    """One line like '36 results: 35 pass/success, 1 fail' from dbt's run_results.json."""
    counts: dict[str, int] = {}
    for result in run_results["results"]:
        status = "pass/success" if result["status"] in {"pass", "success"} else result["status"]
        counts[status] = counts.get(status, 0) + 1
    detail = ", ".join(f"{n} {status}" for status, n in sorted(counts.items()))
    return f"{len(run_results['results'])} results: {detail}"


def change_description(
    sha: str,
    run_url: str,
    coverage_summary: str = "",
    test_summary: str = "",
) -> str:
    """Plain-text description for the change request (ServiceNow shows it as-is)."""
    lines = [
        "Production deploy of the dq_gate dbt project (synthetic data only).",
        "",
        f"Commit: {sha}",
        f"Pipeline run: {run_url}",
    ]
    if test_summary:
        lines += ["", f"dbt tests on the merged code: {test_summary}"]
    if coverage_summary:
        # Drop the HTML comment marker the PR comment uses; ServiceNow would show it literally
        kept = [
            line for line in coverage_summary.strip().splitlines() if not line.startswith("<!--")
        ]
        lines += ["", "Coverage gate:", *kept]
    lines += [
        "",
        "Evidence is attached (dbt JUnit report, run results, coverage summary).",
        "The deploy job waits until this change is approved and Scheduled or Implement.",
    ]
    return "\n".join(lines)
