from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.readiness import run_readiness_audit, write_readiness_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Bottleneck OS production readiness checks")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    audit = run_readiness_audit(ROOT, args.as_of)
    output = Path(args.output) if args.output else ROOT / "reports" / f"{args.as_of}_production_readiness.md"
    path = write_readiness_report(audit, args.as_of, output)
    print(f"{audit['status']} {path}")
    if audit["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
