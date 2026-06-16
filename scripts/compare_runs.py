from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.diffing import write_diff_report
from bottleneck_os.storage import connect, list_runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two persisted Bottleneck OS runs")
    parser.add_argument("--db", default="data/bottleneck_os.sqlite")
    parser.add_argument("--base-run", default=None)
    parser.add_argument("--current-run", default=None)
    parser.add_argument("--output", default="reports/run_diff.md")
    args = parser.parse_args()

    conn = connect(Path(args.db))
    runs = list_runs(conn)
    if args.base_run and args.current_run:
        base_run = args.base_run
        current_run = args.current_run
    elif len(runs) >= 2:
        current_run = runs[0]["run_id"]
        base_run = runs[1]["run_id"]
    else:
        conn.close()
        raise SystemExit("Need at least two runs or pass --base-run and --current-run")

    path = write_diff_report(conn, base_run, current_run, Path(args.output))
    conn.close()
    print(path)


if __name__ == "__main__":
    main()
