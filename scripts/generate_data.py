"""Generate the synthetic CSV files.

python scripts/generate_data.py                     # clean data into data/synthetic
python scripts/generate_data.py --inject-defects    # adds known problems (for gate demos)
"""

from __future__ import annotations

import argparse

from dq_tools.synthetic import DEFAULT_SEED, generate, write_csvs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/synthetic", help="output directory")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--inject-defects", action="store_true")
    args = parser.parse_args()

    tables = generate(seed=args.seed, inject_defects=args.inject_defects)
    paths = write_csvs(tables, args.out)
    for name, path in paths.items():
        print(f"{name}: {len(tables[name])} rows -> {path}")


if __name__ == "__main__":
    main()
