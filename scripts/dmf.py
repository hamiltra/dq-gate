"""Snowflake data metric functions for DQ_DEMO.RAW.

python scripts/dmf.py apply     # create the custom DMF and attach DMFs to the RAW tables (once)
python scripts/dmf.py check     # run every check, write DQ_AUDIT.DMF_RESULTS, exit 1 if any fail
python scripts/dmf.py native    # show what Snowflake recorded for the attached DMFs
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from dq_tools import dmf
from dq_tools.config import SnowflakeSettings
from dq_tools.warehouse import connect


def _print_results(results: list[dmf.Result]) -> None:
    print(f"{'STATUS':6} {'TABLE':13} {'METRIC':32} {'COLUMN':12} {'VALUE':>10} {'MAX':>10}")
    for r in results:
        value = "NULL" if r.value is None else f"{r.value:g}"
        metric = r.metric.removeprefix("SNOWFLAKE.CORE.")
        print(
            f"{r.status:6} {r.table:13} {metric:32} {r.column:12} {value:>10} {r.max_allowed:>10g}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", choices=["apply", "check", "native"])
    parser.add_argument("--no-fail", action="store_true", help="check: print failures but exit 0")
    args = parser.parse_args()

    load_dotenv()
    settings = SnowflakeSettings.from_env()
    conn = connect(settings)
    try:
        if args.command == "apply":
            for sql, outcome in dmf.apply_dmfs(conn):
                print(f"[{outcome}] {sql}")
            return 0
        if args.command == "check":
            ref = os.environ.get("GITHUB_SHA", "local")[:12]
            results = dmf.run_checks(conn, ref=ref)
            _print_results(results)
            bad = dmf.failed(results)
            passed = len(results) - len(bad)
            print(f"\n{passed} passed, {len(bad)} failed; recorded in {dmf.RESULTS_TABLE}")
            return 0 if args.no_fail else int(bool(bad))
        tables = sorted({c.table for c in dmf.CHECKS})
        for row in dmf.native_results(conn, settings.database, tables):
            print(*row, sep="  ")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
