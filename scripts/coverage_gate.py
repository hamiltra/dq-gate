"""Fail when a changed dbt model has no data tests.

python scripts/coverage_gate.py --base origin/main                 # needs target/manifest.json
python scripts/coverage_gate.py --base origin/main --summary-out coverage-summary.md

Changed files come from ``git diff <base>...HEAD``, so CI needs the full history (fetch-depth: 0).
Build the manifest first with ``dbt parse`` (no warehouse connection needed).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dq_tools import coverage


def changed_files(base: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--base", required=True, help="git ref to diff against")
    parser.add_argument("--manifest", default=f"{coverage.DBT_PROJECT_DIR}/target/manifest.json")
    parser.add_argument("--project-dir", default=coverage.DBT_PROJECT_DIR)
    parser.add_argument("--summary-out", help="also write the markdown summary to this file")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    results = coverage.evaluate(manifest, changed_files(args.base), args.project_dir)
    summary = coverage.summary_markdown(results)
    print(summary)
    if args.summary_out:
        Path(args.summary_out).write_text(summary)
    return int(any(not r.covered for r in results))


if __name__ == "__main__":
    sys.exit(main())
