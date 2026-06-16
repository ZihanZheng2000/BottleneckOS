from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.fetcher import archive_manifest_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch URL manifest into archived source markdown files")
    parser.add_argument("--manifest", default="sources/manifest.txt")
    parser.add_argument("--archive-dir", default="archive/sources")
    parser.add_argument("--timeout", default=20, type=int)
    args = parser.parse_args()

    paths = archive_manifest_sources(Path(args.manifest), Path(args.archive_dir), timeout=args.timeout)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
