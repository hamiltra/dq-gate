"""Load the generated CSVs into DQ_DEMO.RAW on Snowflake (reads credentials from .env or env).

python scripts/generate_data.py
python scripts/load_raw.py
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from dq_tools.config import SnowflakeSettings
from dq_tools.load import load_raw
from dq_tools.warehouse import connect


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/synthetic")
    args = parser.parse_args()

    load_dotenv()
    conn = connect(SnowflakeSettings.from_env())
    try:
        counts = load_raw(conn, args.data_dir)
    finally:
        conn.close()
    for table, count in counts.items():
        print(f"RAW.{table}: {count} rows")


if __name__ == "__main__":
    main()
