import csv
from datetime import date

from dq_tools.synthetic import (
    POSITION_COLUMNS,
    PRICE_COLUMNS,
    SECURITY_COLUMNS,
    business_days,
    generate,
    write_csvs,
)


def test_business_days_skips_weekends():
    days = business_days(date(2026, 8, 3), 6)  # Monday start
    assert [d.weekday() for d in days] == [0, 1, 2, 3, 4, 0]
    assert days[-1] == date(2026, 8, 10)


def test_generation_is_deterministic():
    assert generate(seed=7, days=5) == generate(seed=7, days=5)
    assert generate(seed=7, days=5) != generate(seed=8, days=5)


def test_clean_data_has_expected_shape_and_integrity():
    tables = generate(securities=10, portfolios=2, days=5)
    security_ids = {row["security_id"] for row in tables["securities"]}

    assert len(security_ids) == 10 == len(tables["securities"])
    assert len(tables["daily_prices"]) == 10 * 5
    assert all(float(row["close_price"]) > 0 for row in tables["daily_prices"])
    assert {row["security_id"] for row in tables["positions"]} <= security_ids
    assert {row["asset_class"] for row in tables["securities"]} <= {"EQUITY", "BOND", "ETF"}


def test_every_position_has_a_price_on_its_date():
    tables = generate(securities=10, portfolios=2, days=5)
    priced = {(r["security_id"], r["price_date"]) for r in tables["daily_prices"]}
    assert all((r["security_id"], r["as_of_date"]) in priced for r in tables["positions"])


def test_injected_defects_are_present():
    tables = generate(securities=10, portfolios=2, days=5, inject_defects=True)
    ids = [row["security_id"] for row in tables["securities"]]
    assert len(ids) != len(set(ids))  # duplicate
    assert any(float(row["close_price"]) < 0 for row in tables["daily_prices"])
    assert "SEC9999" in {row["security_id"] for row in tables["positions"]}  # orphan


def test_write_csvs_round_trips(tmp_path):
    tables = generate(securities=5, portfolios=1, days=3)
    paths = write_csvs(tables, tmp_path / "out")

    expected = {
        "securities": SECURITY_COLUMNS,
        "daily_prices": PRICE_COLUMNS,
        "positions": POSITION_COLUMNS,
    }
    for name, columns in expected.items():
        with paths[name].open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        assert reader.fieldnames == columns
        assert len(rows) == len(tables[name])
