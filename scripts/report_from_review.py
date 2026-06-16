from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.reporting import write_run_report
from bottleneck_os.review import load_review_repository, review_summary, set_all_claim_statuses


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a report from reviewed claim artifacts")
    parser.add_argument("--review-dir", default="review/current")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", default=None)
    parser.add_argument("--test-results", default=None)
    parser.add_argument("--accept-all", action="store_true")
    args = parser.parse_args()

    review_dir = Path(args.review_dir)
    if args.accept_all:
        set_all_claim_statuses(review_dir, "accepted")
    repo = load_review_repository(review_dir, include_statuses={"accepted"})
    as_of = date.fromisoformat(args.as_of)
    output = Path(args.output) if args.output else Path("reports") / f"{as_of.isoformat()}_reviewed_report.md"
    test_results = Path(args.test_results) if args.test_results else None
    path = write_run_report(repo, as_of, output, test_results)
    summary = review_summary(review_dir)
    print(f"accepted={summary['accepted']} pending={summary['pending']} rejected={summary['rejected']} report={path}")


if __name__ == "__main__":
    main()
