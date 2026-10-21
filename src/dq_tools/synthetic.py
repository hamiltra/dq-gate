"""Deterministic synthetic financial data: security master, daily prices, positions.

Everything here is made up. Tickers are SYNxxx, names are "Synthetic ..." and prices follow a
seeded random walk, so the same seed always produces identical files. No real or proprietary
data is used.

``inject_defects=True`` adds a few known problems (a duplicate security, a negative price,
an orphan position). The default data is clean so the dbt tests pass; the defect flag exists
to demonstrate the quality gate failing on purpose.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SECURITY_COLUMNS = [
    "security_id",
    "ticker",
    "security_name",
    "asset_class",
    "sector",
    "currency",
    "issue_date",
]
PRICE_COLUMNS = ["security_id", "price_date", "close_price", "volume"]
POSITION_COLUMNS = ["portfolio_id", "security_id", "as_of_date", "quantity"]

ASSET_CLASSES = ["EQUITY", "BOND", "ETF"]
SECTORS = ["Technology", "Financials", "Healthcare", "Energy", "Utilities", "Industrials"]
CURRENCIES = ["USD", "USD", "USD", "EUR"]  # mostly USD

DEFAULT_SEED = 42
DEFAULT_START = date(2026, 8, 3)  # a Monday
DEFAULT_DAYS = 55  # business days of history
DEFAULT_SECURITIES = 40
DEFAULT_PORTFOLIOS = 5
HOLDINGS_PER_PORTFOLIO = 12


def business_days(start: date, count: int) -> list[date]:
    """Return ``count`` weekdays beginning on or after ``start``."""
    days: list[date] = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def make_securities(rng: random.Random, count: int) -> list[dict]:
    rows = []
    for i in range(1, count + 1):
        rows.append(
            {
                "security_id": f"SEC{i:04d}",
                "ticker": f"SYN{i:03d}",
                "security_name": f"Synthetic Holdings {i:03d}",
                "asset_class": rng.choice(ASSET_CLASSES),
                "sector": rng.choice(SECTORS),
                "currency": rng.choice(CURRENCIES),
                "issue_date": (date(2010, 1, 1) + timedelta(days=rng.randint(0, 5000))).isoformat(),
            }
        )
    return rows


def make_prices(rng: random.Random, securities: list[dict], days: list[date]) -> list[dict]:
    rows = []
    for security in securities:
        price = rng.uniform(20, 300)
        for day in days:
            price = max(1.0, price * (1 + rng.gauss(0, 0.012)))
            rows.append(
                {
                    "security_id": security["security_id"],
                    "price_date": day.isoformat(),
                    "close_price": f"{price:.4f}",
                    "volume": rng.randint(50_000, 5_000_000),
                }
            )
    return rows


def make_positions(
    rng: random.Random, securities: list[dict], days: list[date], portfolios: int
) -> list[dict]:
    rows = []
    for p in range(1, portfolios + 1):
        holdings = rng.sample(securities, min(HOLDINGS_PER_PORTFOLIO, len(securities)))
        for security in holdings:
            quantity = rng.randint(1, 200) * 100
            for day in days:
                if rng.random() < 0.05:  # occasional rebalance
                    quantity = max(100, quantity + rng.randint(-5, 5) * 100)
                rows.append(
                    {
                        "portfolio_id": f"PF{p:02d}",
                        "security_id": security["security_id"],
                        "as_of_date": day.isoformat(),
                        "quantity": f"{quantity:.2f}",
                    }
                )
    return rows


def inject_known_defects(securities: list[dict], prices: list[dict], positions: list[dict]) -> None:
    """Add deliberate data problems in place (used to show the gate failing)."""
    securities.append(dict(securities[0]))  # duplicate security_id and ticker
    prices[0] = {**prices[0], "close_price": "-1.0000"}  # negative price
    positions.append(
        {
            "portfolio_id": "PF01",
            "security_id": "SEC9999",  # not in the security master
            "as_of_date": prices[0]["price_date"],
            "quantity": "100.00",
        }
    )


def generate(
    seed: int = DEFAULT_SEED,
    start: date = DEFAULT_START,
    days: int = DEFAULT_DAYS,
    securities: int = DEFAULT_SECURITIES,
    portfolios: int = DEFAULT_PORTFOLIOS,
    inject_defects: bool = False,
) -> dict[str, list[dict]]:
    """Return the three tables as lists of row dicts."""
    rng = random.Random(seed)
    day_list = business_days(start, days)
    security_rows = make_securities(rng, securities)
    price_rows = make_prices(rng, security_rows, day_list)
    position_rows = make_positions(rng, security_rows, day_list, portfolios)
    if inject_defects:
        inject_known_defects(security_rows, price_rows, position_rows)
    return {
        "securities": security_rows,
        "daily_prices": price_rows,
        "positions": position_rows,
    }


def write_csvs(tables: dict[str, list[dict]], out_dir: str | Path) -> dict[str, Path]:
    """Write each table to ``<out_dir>/<name>.csv`` and return the paths."""
    columns = {
        "securities": SECURITY_COLUMNS,
        "daily_prices": PRICE_COLUMNS,
        "positions": POSITION_COLUMNS,
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, rows in tables.items():
        path = out / f"{name}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns[name])
            writer.writeheader()
            writer.writerows(rows)
        paths[name] = path
    return paths
