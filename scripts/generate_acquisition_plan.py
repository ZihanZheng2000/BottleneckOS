from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.acquisition import write_acquisition_plan
from bottleneck_os.repository import build_seed_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate source acquisition plan for Bottleneck OS coverage gaps")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    output = Path(args.output) if args.output else ROOT / "reports" / f"{as_of.isoformat()}_acquisition_plan.md"
    path = write_acquisition_plan(build_seed_repository(), as_of, output)
    print(path)


if __name__ == "__main__":
    main()
