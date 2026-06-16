"""Fetch RSS/API feeds and archive items as source markdown files.

Run manually whenever you want fresh data:
    py scripts/fetch_feeds.py
    py scripts/fetch_feeds.py --feeds sources/feeds.txt --archive-dir archive/sources
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.rss_fetcher import FeedConfig, fetch_feed_to_archive, parse_feed_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch RSS/API feeds into archived source markdown files")
    parser.add_argument("--feeds", default="sources/feeds.txt", help="Feed config file (default: sources/feeds.txt)")
    parser.add_argument("--archive-dir", default="archive/sources", help="Output directory for archived source files")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    args = parser.parse_args()

    feeds_path = Path(args.feeds)
    if not feeds_path.exists():
        print(f"Feed config not found: {feeds_path}")
        print(f"Create it or copy from sources/feeds.txt")
        sys.exit(1)

    configs = parse_feed_config(feeds_path)
    if not configs:
        print("No feeds found in config file.")
        sys.exit(0)

    archive_dir = Path(args.archive_dir)
    total_new = 0
    total_skipped = 0

    for config in configs:
        print(f"\n[{config.source_name}]")
        print(f"  {config.rss_url[:80]}")
        try:
            before = set(archive_dir.glob("*.md")) if archive_dir.exists() else set()
            paths = fetch_feed_to_archive(config, archive_dir, timeout=args.timeout)
            after = set(paths)
            new_count = sum(1 for p in paths if p not in before)
            skip_count = len(paths) - new_count
            print(f"  {new_count} new, {skip_count} already archived ({len(paths)} total items)")
            total_new += new_count
            total_skipped += skip_count
        except Exception as exc:
            print(f"  ERROR: {exc}")

    print(f"\nDone: {total_new} new items archived, {total_skipped} skipped (already exist)")
    print(f"Archive: {archive_dir.resolve()}")
    print(f"\nNext step:")
    print(f"  py scripts/extract_claims.py --source-dir {args.archive_dir} --llm --auto-accept")


if __name__ == "__main__":
    main()
