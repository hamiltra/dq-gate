from datetime import UTC, datetime

import pytest

from dq_tools import dmf


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._last = None

    def execute(self, sql, params=None):
        self.conn.log.append((sql, params))
        for needle, outcome in self.conn.behaviour.items():
            if needle in sql:
                if isinstance(outcome, Exception):
                    raise outcome
                self._last = outcome
                return
        self._last = (0,)

    def fetchone(self):
        return self._last

    def fetchall(self):
        return [self._last] if self._last else []

    def close(self):
        pass


class FakeConnection:
    def __init__(self, behaviour=None):
        self.log = []
        self.behaviour = behaviour or {}

    def cursor(self):
        return FakeCursor(self)

    def statements(self):
        return [sql for sql, _ in self.log]


def test_custom_dmf_sql_is_idempotent_and_counts_non_positive_values():
    sql = dmf.create_custom_dmf_sql()
    assert sql.startswith("CREATE DATA METRIC FUNCTION IF NOT EXISTS DQ_AUDIT.NON_POSITIVE_COUNT")
    assert "arg_t TABLE(arg_c NUMBER)" in sql
    assert "WHERE arg_c <= 0" in sql


def test_add_dmf_sql_lists_columns_and_freshness_uses_none():
    null_check = dmf.Check("DAILY_PRICES", "SNOWFLAKE.CORE.NULL_COUNT", "security_id", 0)
    freshness = next(c for c in dmf.CHECKS if c.metric.endswith("FRESHNESS"))
    assert dmf.add_dmf_sql(null_check) == (
        "ALTER TABLE RAW.DAILY_PRICES ADD DATA METRIC FUNCTION "
        "SNOWFLAKE.CORE.NULL_COUNT ON (security_id)"
    )
    assert dmf.add_dmf_sql(freshness).endswith("SNOWFLAKE.CORE.FRESHNESS ON ()")


def test_adhoc_sql_for_system_custom_and_cast_columns():
    system = dmf.Check("SECURITIES", "SNOWFLAKE.CORE.DUPLICATE_COUNT", "security_id", 0)
    custom = dmf.Check("DAILY_PRICES", dmf.CUSTOM_DMF, "close_price", 0, custom=True)
    freshness = next(c for c in dmf.CHECKS if c.metric.endswith("FRESHNESS"))
    assert dmf.adhoc_sql(system) == (
        "SELECT SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT security_id FROM RAW.SECURITIES)"
    )
    assert dmf.adhoc_sql(custom) == (
        "SELECT DQ_AUDIT.NON_POSITIVE_COUNT((SELECT close_price FROM RAW.DAILY_PRICES))"
    )
    assert dmf.adhoc_sql(freshness).startswith("SELECT DATEDIFF('second', MAX(loaded_at)")
    assert "FROM RAW.DAILY_PRICES" in dmf.adhoc_sql(freshness)


def test_default_checks_cover_three_system_dmfs_and_one_custom():
    system = {c.metric for c in dmf.CHECKS if not c.custom}
    assert {
        "SNOWFLAKE.CORE.NULL_COUNT",
        "SNOWFLAKE.CORE.DUPLICATE_COUNT",
        "SNOWFLAKE.CORE.FRESHNESS",
    } <= system
    assert sum(c.custom for c in dmf.CHECKS) == 1


def test_apply_creates_function_schedules_each_table_once_then_attaches():
    conn = FakeConnection()
    done = dmf.apply_dmfs(conn)
    sql = conn.statements()
    assert sql[0].startswith("CREATE DATA METRIC FUNCTION")
    schedules = [s for s in sql if "DATA_METRIC_SCHEDULE" in s]
    assert len(schedules) == 2  # DAILY_PRICES and SECURITIES
    assert sum("ADD DATA METRIC FUNCTION" in s for s in sql) == len(dmf.CHECKS)
    assert all(outcome == "ok" for _, outcome in done)


def test_apply_tolerates_already_attached_but_raises_other_errors():
    conn = FakeConnection(
        {"NULL_COUNT": RuntimeError("Data metric function is already associated")}
    )
    outcomes = [o for _, o in dmf.apply_dmfs(conn)]
    assert "already attached" in outcomes

    broken = FakeConnection({"NULL_COUNT": RuntimeError("Insufficient privileges")})
    with pytest.raises(RuntimeError, match="Insufficient"):
        dmf.apply_dmfs(broken)


def test_run_checks_passes_when_every_value_is_within_its_limit():
    conn = FakeConnection()
    results = dmf.run_checks(conn, ref="abc123", run_id="r1")
    assert [r.status for r in results] == [dmf.PASS] * len(dmf.CHECKS)
    assert dmf.failed(results) == []


def test_run_checks_fails_on_bad_values_and_on_null_and_records_every_row():
    conn = FakeConnection(
        {
            "NON_POSITIVE_COUNT": (1,),  # negative price present
            "DUPLICATE_COUNT": (2,),  # duplicate security
            "DATEDIFF": (None,),  # no value returned
        }
    )
    now = datetime(2026, 10, 22, 9, 0, tzinfo=UTC)
    results = dmf.run_checks(conn, ref="abc123", run_id="r1", now=now)

    by_metric = {r.metric.split(".")[-1]: r for r in results}
    assert by_metric["NON_POSITIVE_COUNT"].status == dmf.FAIL
    assert by_metric["FRESHNESS"].status == dmf.FAIL
    assert by_metric["FRESHNESS"].value is None
    assert len(dmf.failed(results)) == 3

    inserts = [(s, p) for s, p in conn.log if s.startswith("INSERT INTO DQ_AUDIT.DMF_RESULTS")]
    assert len(inserts) == len(dmf.CHECKS)
    params = inserts[0][1]
    assert params[0] == "r1" and params[2] == "abc123"
    assert params[1] == datetime(2026, 10, 22, 9, 0)  # naive UTC for TIMESTAMP_NTZ


def test_run_checks_creates_the_results_table_first():
    conn = FakeConnection()
    dmf.run_checks(conn)
    assert conn.statements()[0].startswith("CREATE TABLE IF NOT EXISTS DQ_AUDIT.DMF_RESULTS")


def test_native_results_sql_uses_fully_qualified_table_name():
    sql = dmf.native_results_sql("DQ_DEMO", "DAILY_PRICES")
    assert "SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS" in sql
    assert "REF_ENTITY_NAME => 'DQ_DEMO.RAW.DAILY_PRICES'" in sql
    assert "REF_ENTITY_DOMAIN => 'TABLE'" in sql


def test_native_results_collects_rows_for_each_table():
    conn = FakeConnection({"DATA_QUALITY_MONITORING_RESULTS": ("t", "n", "m", 0)})
    rows = dmf.native_results(conn, "DQ_DEMO", ["A", "B"])
    assert len(rows) == 2
