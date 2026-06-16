from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.storage import connect
from bottleneck_os.trends import write_trends_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate historical trend report from persisted run snapshots")
    parser.add_argument("--db", default="data/bottleneck_os.sqlite")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    output = Path(args.output) if args.output else Path("reports") / f"{as_of.isoformat()}_historical_trends.md"
    conn = connect(Path(args.db))
    path = write_trends_report(conn, as_of, output)
    conn.close()
    print(path)


if __name__ == "__main__":
    main()
