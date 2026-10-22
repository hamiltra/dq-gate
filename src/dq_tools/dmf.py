"""Snowflake data metric functions (DMFs): attach them to RAW tables and run them as a gate.

Two ways the same checks are used:

* ``apply_dmfs`` attaches the DMFs to the tables so Snowflake evaluates them itself whenever the
  data changes (results appear in ``SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS``).
* ``run_checks`` calls each DMF directly (ad hoc), compares the value with a threshold and writes
  one row per check to ``DQ_AUDIT.DMF_RESULTS``. CI uses this to pass or fail a pull request.

The functions only need a DB-API style connection, so they are unit-tested with a fake connection.
The SQL builders are plain functions so the statements can be read and tested without Snowflake.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

RAW_SCHEMA = "RAW"
AUDIT_SCHEMA = "DQ_AUDIT"
RESULTS_TABLE = f"{AUDIT_SCHEMA}.DMF_RESULTS"
CUSTOM_DMF = f"{AUDIT_SCHEMA}.NON_POSITIVE_COUNT"
SCHEDULE = "TRIGGER_ON_CHANGES"
THIRTY_DAYS_SECONDS = 30 * 24 * 60 * 60

PASS = "PASS"
FAIL = "FAIL"


@dataclass(frozen=True)
class Check:
    """One data quality check: a DMF, the column it looks at and the largest value that passes."""

    table: str
    metric: str
    column: str
    max_allowed: float
    custom: bool = False
    # Expression selected for ad hoc calls (defaults to the column itself)
    query_expr: str | None = None
    # Complete SQL to use for the ad hoc value instead of calling the DMF directly
    adhoc_override: str | None = None
    # Columns for ADD DATA METRIC FUNCTION ... ON (...); FRESHNESS uses no column when attached
    attach_on: tuple[str, ...] | None = None

    @property
    def attach_columns(self) -> tuple[str, ...]:
        return (self.column,) if self.attach_on is None else self.attach_on


CHECKS: tuple[Check, ...] = (
    Check("DAILY_PRICES", "SNOWFLAKE.CORE.NULL_COUNT", "security_id", 0),
    Check("DAILY_PRICES", "SNOWFLAKE.CORE.NULL_COUNT", "close_price", 0),
    Check("SECURITIES", "SNOWFLAKE.CORE.DUPLICATE_COUNT", "security_id", 0),
    # Seconds since the data was last loaded. Snowflake rejects a direct FRESHNESS call on this
    # column, so the ad hoc value uses the equivalent SQL; the real FRESHNESS DMF is still attached
    # to the table (it measures time since the last change) and recorded by Snowflake itself.
    Check(
        "DAILY_PRICES",
        "SNOWFLAKE.CORE.FRESHNESS",
        "loaded_at",
        THIRTY_DAYS_SECONDS,
        adhoc_override=(
            "SELECT DATEDIFF('second', MAX(loaded_at), CURRENT_TIMESTAMP()::TIMESTAMP_NTZ) "
            f"FROM {RAW_SCHEMA}.DAILY_PRICES"
        ),
        attach_on=(),
    ),
    Check("DAILY_PRICES", CUSTOM_DMF, "close_price", 0, custom=True),
)


@dataclass(frozen=True)
class Result:
    table: str
    metric: str
    column: str
    value: float | None
    max_allowed: float
    status: str


# ---------------------------------------------------------------- SQL builders


def create_custom_dmf_sql() -> str:
    """Custom DMF: how many values are zero or negative (NULLs are ignored)."""
    return (
        f"CREATE DATA METRIC FUNCTION IF NOT EXISTS {CUSTOM_DMF}(arg_t TABLE(arg_c NUMBER)) "
        "RETURNS NUMBER AS $$ SELECT COUNT(*) FROM arg_t WHERE arg_c <= 0 $$"
    )


def set_schedule_sql(table: str, schema: str = RAW_SCHEMA) -> str:
    return f"ALTER TABLE {schema}.{table} SET DATA_METRIC_SCHEDULE = '{SCHEDULE}'"


def add_dmf_sql(check: Check, schema: str = RAW_SCHEMA) -> str:
    columns = ", ".join(check.attach_columns)
    return (
        f"ALTER TABLE {schema}.{check.table} ADD DATA METRIC FUNCTION {check.metric} ON ({columns})"
    )


def adhoc_sql(check: Check, schema: str = RAW_SCHEMA) -> str:
    """Call the DMF directly on one column. System DMFs take the query as is; a custom DMF takes
    its table argument in parentheses."""
    if check.adhoc_override:
        return check.adhoc_override
    expr = check.query_expr or check.column
    query = f"SELECT {expr} FROM {schema}.{check.table}"
    if check.custom:
        return f"SELECT {check.metric}(({query}))"
    return f"SELECT {check.metric}({query})"


def create_results_table_sql() -> str:
    return (
        f"CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (\n"
        "  run_id VARCHAR,\n"
        "  run_ts TIMESTAMP_NTZ,\n"
        "  ref VARCHAR,\n"
        "  table_name VARCHAR,\n"
        "  metric VARCHAR,\n"
        "  column_name VARCHAR,\n"
        "  value NUMBER(38,4),\n"
        "  max_allowed NUMBER(38,4),\n"
        "  status VARCHAR\n)"
    )


def insert_result_sql() -> str:
    return (
        f"INSERT INTO {RESULTS_TABLE} "
        "(run_id, run_ts, ref, table_name, metric, column_name, value, max_allowed, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )


def native_results_sql(database: str, table: str, schema: str = RAW_SCHEMA) -> str:
    """Results Snowflake produced for the DMFs attached to a table (scheduled evaluations)."""
    return (
        "SELECT measurement_time, table_name, metric_name, value "
        "FROM TABLE(SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS("
        f"REF_ENTITY_NAME => '{database}.{schema}.{table}', REF_ENTITY_DOMAIN => 'TABLE')) "
        "ORDER BY measurement_time DESC"
    )


# ------------------------------------------------------------------ operations


def apply_dmfs(conn, checks: tuple[Check, ...] = CHECKS) -> list[tuple[str, str]]:
    """Create the custom DMF and attach every check's DMF to its table. Safe to run again.

    Returns (statement, outcome) pairs where outcome is 'ok' or 'already attached'.
    """
    cursor = conn.cursor()
    done: list[tuple[str, str]] = []
    try:
        for sql in [create_custom_dmf_sql(), *[set_schedule_sql(t) for t in _tables(checks)]]:
            cursor.execute(sql)
            done.append((sql, "ok"))
        for check in checks:
            sql = add_dmf_sql(check)
            try:
                cursor.execute(sql)
                done.append((sql, "ok"))
            except Exception as exc:  # the connector raises its own error types
                if "already" not in str(exc).lower():
                    raise
                done.append((sql, "already attached"))
    finally:
        cursor.close()
    return done


def run_checks(
    conn,
    checks: tuple[Check, ...] = CHECKS,
    ref: str = "local",
    run_id: str | None = None,
    now: datetime | None = None,
) -> list[Result]:
    """Evaluate every check, record the outcome in DQ_AUDIT.DMF_RESULTS and return the results."""
    run_id = run_id or uuid.uuid4().hex
    run_ts = (now or datetime.now(UTC)).replace(tzinfo=None)
    cursor = conn.cursor()
    results: list[Result] = []
    try:
        cursor.execute(create_results_table_sql())
        for check in checks:
            cursor.execute(adhoc_sql(check))
            row = cursor.fetchone()
            value = None if row is None or row[0] is None else float(row[0])
            status = PASS if value is not None and value <= check.max_allowed else FAIL
            result = Result(
                check.table, check.metric, check.column, value, check.max_allowed, status
            )
            results.append(result)
            cursor.execute(
                insert_result_sql(),
                (
                    run_id,
                    run_ts,
                    ref,
                    result.table,
                    result.metric,
                    result.column,
                    result.value,
                    result.max_allowed,
                    result.status,
                ),
            )
    finally:
        cursor.close()
    return results


def native_results(conn, database: str, tables: list[str]) -> list[tuple]:
    """Rows Snowflake recorded for the attached DMFs, newest first (can lag a few minutes)."""
    cursor = conn.cursor()
    rows: list[tuple] = []
    try:
        for table in tables:
            cursor.execute(native_results_sql(database, table))
            rows.extend(cursor.fetchall())
    finally:
        cursor.close()
    return rows


def failed(results: list[Result]) -> list[Result]:
    return [r for r in results if r.status == FAIL]


def _tables(checks: tuple[Check, ...]) -> list[str]:
    seen: list[str] = []
    for check in checks:
        if check.table not in seen:
            seen.append(check.table)
    return seen
