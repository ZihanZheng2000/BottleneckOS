from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.repository import build_seed_repository
from bottleneck_os.review import load_review_repository
from bottleneck_os.storage import connect, list_runs, persist_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist Bottleneck OS run snapshots to SQLite")
    parser.add_argument("--db", default="data/bottleneck_os.sqlite")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--source", default="seed")
    parser.add_argument("--review-dir", default=None)
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    conn = connect(Path(args.db))
    if args.list:
        for row in list_runs(conn):
            print(
                f"{row['run_id']} as_of={row['as_of']} source={row['source']} "
                f"documents={row['document_count']} claims={row['claim_count']} report={row['report_path']}"
            )
        conn.close()
        return

    repo = load_review_repository(Path(args.review_dir)) if args.review_dir else build_seed_repository()
    run_id = persist_run(
        conn,
        repo,
        date.fromisoformat(args.as_of),
        args.source,
        Path(args.report_path) if args.report_path else None,
    )
    print(run_id)
    conn.close()


if __name__ == "__main__":
    main()
