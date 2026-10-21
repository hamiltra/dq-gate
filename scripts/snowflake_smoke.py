"""Live Snowflake connection check (run by hand, never in CI)."""

import os

import snowflake.connector
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        private_key_file=os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]),
    )
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), "
            "CURRENT_DATABASE(), CURRENT_VERSION()"
        )
        print("Connected:", cur.fetchone())
        cur.execute("SHOW SCHEMAS IN DATABASE DQ_DEMO")
        print("Schemas:", sorted(row[1] for row in cur.fetchall()))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
