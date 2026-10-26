"""Convert dbt's run_results.json to JUnit XML.

python scripts/results_to_junit.py      # dbt/dq_gate/target/run_results.json -> dbt-junit.xml
python scripts/results_to_junit.py --run-results path/run_results.json --out report.xml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dq_tools.junit import to_junit


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--run-results", default="dbt/dq_gate/target/run_results.json")
    parser.add_argument("--out", default="dbt-junit.xml")
    args = parser.parse_args()

    run_results = json.loads(Path(args.run_results).read_text())
    Path(args.out).write_text(to_junit(run_results))
    print(f"{len(run_results['results'])} results -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
