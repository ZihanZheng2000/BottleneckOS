from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.extractor import extract_repository_from_directory
from bottleneck_os.fetcher import archive_manifest_sources
from bottleneck_os.reporting import write_run_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract claims from source markdown files and generate a report")
    parser.add_argument("--source-dir", default="sources")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--archive-dir", default="archive/sources")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", default=None)
    parser.add_argument("--test-results", default=None)
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    source_dir = Path(args.source_dir)
    if args.manifest:
        archive_manifest_sources(Path(args.manifest), Path(args.archive_dir))
        source_dir = Path(args.archive_dir)
    if not source_dir.exists():
        raise SystemExit(f"Source directory does not exist: {source_dir}")
    repo = extract_repository_from_directory(source_dir)
    if not repo.documents:
        raise SystemExit(f"No .md source files found in: {source_dir}")
    output = Path(args.output) if args.output else Path("reports") / f"{as_of.isoformat()}_extracted_report.md"
    test_results = Path(args.test_results) if args.test_results else None
    path = write_run_report(repo, as_of, output, test_results)
    print(f"documents={len(repo.documents)} claims={len(repo.claims)} report={path}")


if __name__ == "__main__":
    main()
