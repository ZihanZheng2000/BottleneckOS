from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.reporting import write_run_report
from bottleneck_os.repository import build_seed_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Bottleneck OS run report")
    parser.add_argument("--output", default=None)
    parser.add_argument("--test-results", default=None)
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    output = Path(args.output) if args.output else Path("reports") / f"{as_of.isoformat()}_report.md"
    test_results = (
        Path(args.test_results)
        if args.test_results
        else Path("reports") / f"{as_of.isoformat()}_test-results.txt"
    )
    path = write_run_report(
        build_seed_repository(),
        as_of,
        output,
        test_results,
    )
    print(path)


if __name__ == "__main__":
    main()
