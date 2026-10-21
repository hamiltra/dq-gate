"""Load the synthetic CSVs into Snowflake RAW tables (PUT to the table stage, then COPY INTO).

The functions only need a DB-API style connection (``cursor()``, ``execute()``, ``fetchone()``),
so they are unit-tested with a fake connection and never touch a real account in CI.
"""

from __future__ import annotations

from pathlib import Path

# table name -> (column definitions, CSV column count)
RAW_TABLES: dict[str, list[tuple[str, str]]] = {
    "SECURITIES": [
        ("security_id", "VARCHAR"),
        ("ticker", "VARCHAR"),
        ("security_name", "VARCHAR"),
        ("asset_class", "VARCHAR"),
        ("sector", "VARCHAR"),
        ("currency", "VARCHAR"),
        ("issue_date", "DATE"),
    ],
    "DAILY_PRICES": [
        ("security_id", "VARCHAR"),
        ("price_date", "DATE"),
        ("close_price", "NUMBER(18,4)"),
        ("volume", "NUMBER(18,0)"),
    ],
    "POSITIONS": [
        ("portfolio_id", "VARCHAR"),
        ("security_id", "VARCHAR"),
        ("as_of_date", "DATE"),
        ("quantity", "NUMBER(18,2)"),
    ],
}

# CSV file name (without extension) for each table
CSV_FOR_TABLE = {
    "SECURITIES": "securities",
    "DAILY_PRICES": "daily_prices",
    "POSITIONS": "positions",
}


def create_table_sql(table: str, schema: str = "RAW") -> str:
    columns = ",\n  ".join(f"{name} {dtype}" for name, dtype in RAW_TABLES[table])
    return (
        f"CREATE TABLE IF NOT EXISTS {schema}.{table} (\n  {columns},\n"
        "  loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()\n)"
    )


def put_sql(table: str, csv_path: Path, schema: str = "RAW") -> str:
    path = csv_path.resolve().as_posix().replace("'", "\\'")
    return f"PUT 'file://{path}' @{schema}.%{table} OVERWRITE = TRUE AUTO_COMPRESS = TRUE"


def copy_sql(table: str, schema: str = "RAW") -> str:
    names = [name for name, _ in RAW_TABLES[table]]
    # Explicit casts: the staged CSV fields arrive as text.
    selected = ", ".join(f"${i}::{dtype}" for i, (_, dtype) in enumerate(RAW_TABLES[table], 1))
    return (
        f"COPY INTO {schema}.{table} ({', '.join(names)}) "
        f"FROM (SELECT {selected} FROM @{schema}.%{table}) "
        "FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' "
        "NULL_IF = ('')) PURGE = TRUE FORCE = TRUE"
    )


def load_raw(conn, data_dir: str | Path, schema: str = "RAW") -> dict[str, int]:
    """Reload every RAW table from ``data_dir`` and return the row count per table.

    Each run truncates and reloads, so repeated runs give the same result.
    """
    data_dir = Path(data_dir)
    counts: dict[str, int] = {}
    cursor = conn.cursor()
    try:
        for table, csv_name in CSV_FOR_TABLE.items():
            csv_path = data_dir / f"{csv_name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing {csv_path}; run scripts/generate_data.py first")
            cursor.execute(create_table_sql(table, schema))
            cursor.execute(f"TRUNCATE TABLE {schema}.{table}")
            cursor.execute(put_sql(table, csv_path, schema))
            cursor.execute(copy_sql(table, schema))
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
            counts[table] = int(cursor.fetchone()[0])
    finally:
        cursor.close()
    return counts
