import pytest

from dq_tools import change


class FakeClient:
    """Returns one (state, approval) pair per get_change call, repeating the last."""

    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.calls = 0

    def get_change(self, sys_id):
        state, approval = self.sequence[min(self.calls, len(self.sequence) - 1)]
        self.calls += 1
        return {"number": "CHG0030002", "state": state, "approval": approval}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def run(sequence, timeout=900, interval=30):
    client, clock, logs = FakeClient(sequence), FakeClock(), []
    result = change.wait_for_approval(
        client, "abc123", timeout, interval, log=logs.append, sleep=clock.sleep, clock=clock
    )
    return result, client, logs


@pytest.mark.parametrize(
    ("state", "approval", "expected"),
    [
        (change.SCHEDULED, "approved", change.APPROVED),
        (change.IMPLEMENT, "approved", change.APPROVED),
        (change.AUTHORIZE, "approved", change.WAITING),  # approved but not scheduled yet
        (change.NEW, "not requested", change.WAITING),
        (change.ASSESS, "requested", change.WAITING),
        (change.AUTHORIZE, "rejected", change.REJECTED),
        (change.CANCELED, "approved", change.REJECTED),
        (change.CLOSED, "approved", change.REJECTED),  # closed changes cannot be reused
    ],
)
def test_decide(state, approval, expected):
    assert change.decide(state, approval) == expected


def test_wait_returns_once_approved_and_logs_only_changes():
    result, client, logs = run(
        [
            (change.NEW, "not requested"),
            (change.NEW, "not requested"),
            (change.ASSESS, "requested"),
            (change.SCHEDULED, "approved"),
        ]
    )
    assert result.outcome == change.APPROVED
    assert (result.number, result.state_label, result.waited_seconds) == (
        "CHG0030002",
        "Scheduled",
        90,
    )
    assert client.calls == 4
    assert logs == [
        "CHG0030002: state=New approval=not requested",
        "CHG0030002: state=Assess approval=requested",
        "CHG0030002: state=Scheduled approval=approved",
    ]


def test_wait_stops_at_once_on_rejection():
    result, client, _ = run([(change.AUTHORIZE, "rejected")])
    assert result.outcome == change.REJECTED
    assert client.calls == 1


def test_wait_times_out_without_sleeping_past_the_limit():
    result, client, _ = run([(change.NEW, "not requested")], timeout=100, interval=30)
    assert result.outcome == change.TIMED_OUT
    # polls at 0, 30, 60, 90; another sleep would pass 100 seconds
    assert client.calls == 4
    assert result.waited_seconds == 90


def test_servicenow_utc_converts_to_utc():
    from datetime import datetime, timedelta, timezone

    pdt = timezone(timedelta(hours=-7))
    assert change.servicenow_utc(datetime(2026, 10, 27, 12, 46, 17, tzinfo=pdt)) == (
        "2026-10-27 19:46:17"
    )


def test_results_summary_counts_statuses():
    run_results = {
        "results": [
            {"status": "success"},
            {"status": "pass"},
            {"status": "fail"},
            {"status": "skipped"},
        ]
    }
    assert change.results_summary(run_results) == "4 results: 1 fail, 2 pass/success, 1 skipped"


def test_change_description_includes_evidence_without_the_comment_marker():
    text = change.change_description(
        "0123456789abcdef",
        "https://github.com/o/r/actions/runs/1",
        coverage_summary="<!-- dq-gate:coverage-gate -->\n## Coverage gate\n\n**Passed:** all 1",
        test_summary="36 results: 36 pass/success",
    )
    assert "Commit: 0123456789abcdef" in text
    assert "Pipeline run: https://github.com/o/r/actions/runs/1" in text
    assert "dbt tests on the merged code: 36 results: 36 pass/success" in text
    assert "## Coverage gate" in text and "<!--" not in text
