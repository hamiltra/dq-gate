from pathlib import Path

import pytest

from dq_tools.load import copy_sql, create_table_sql, load_raw, put_sql
from dq_tools.synthetic import generate, write_csvs


class FakeCursor:
    def __init__(self, log: list[str]):
        self.log = log
        self._count = 42

    def execute(self, sql: str):
        self.log.append(sql)

    def fetchone(self):
        return (self._count,)

    def close(self):
        self.log.append("CLOSE")


class FakeConnection:
    def __init__(self):
        self.log: list[str] = []

    def cursor(self):
        return FakeCursor(self.log)


def test_create_table_sql_has_loaded_at_default():
    sql = create_table_sql("SECURITIES")
    assert sql.startswith("CREATE TABLE IF NOT EXISTS RAW.SECURITIES")
    assert "security_id VARCHAR" in sql
    assert "loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()" in sql


def test_copy_sql_selects_positional_columns_without_loaded_at():
    sql = copy_sql("DAILY_PRICES")
    assert "COPY INTO RAW.DAILY_PRICES (security_id, price_date, close_price, volume)" in sql
    assert (
        "SELECT $1::VARCHAR, $2::DATE, $3::NUMBER(18,4), $4::NUMBER(18,0) FROM @RAW.%DAILY_PRICES"
    ) in sql
    assert "loaded_at" not in sql
    assert "SKIP_HEADER = 1" in sql


def test_put_sql_uses_absolute_path_and_table_stage(tmp_path):
    sql = put_sql("POSITIONS", tmp_path / "positions.csv")
    assert sql.startswith(f"PUT 'file://{tmp_path.resolve().as_posix()}/positions.csv'")
    assert "@RAW.%POSITIONS" in sql


def test_load_raw_runs_statements_in_order_and_returns_counts(tmp_path):
    write_csvs(generate(securities=3, portfolios=1, days=2), tmp_path)
    conn = FakeConnection()

    counts = load_raw(conn, tmp_path)

    assert counts == {"SECURITIES": 42, "DAILY_PRICES": 42, "POSITIONS": 42}
    kinds = [s.split()[0] for s in conn.log if s != "CLOSE"]
    # per table: CREATE, TRUNCATE, PUT, COPY, SELECT
    assert kinds == ["CREATE", "TRUNCATE", "PUT", "COPY", "SELECT"] * 3
    assert conn.log[-1] == "CLOSE"


def test_load_raw_fails_clearly_when_csv_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="generate_data.py"):
        load_raw(FakeConnection(), Path(tmp_path))
