from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bottleneck_os.fetcher import archive_manifest_sources
from bottleneck_os.review import write_review_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract source claims into review JSONL artifacts")
    parser.add_argument("--source-dir", default="sources")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--archive-dir", default="archive/sources")
    parser.add_argument("--review-dir", default="review/current")
    parser.add_argument("--auto-accept", action="store_true")
    parser.add_argument("--llm", action="store_true", help="Use LLM for extraction instead of keyword rules")
    parser.add_argument(
        "--provider", default="auto", choices=["auto", "openai", "anthropic"],
        help="LLM provider (default: auto-detect from .env)"
    )
    parser.add_argument("--model", default=None, help="Override model (e.g. gpt-4o-mini, claude-haiku-4-5)")
    parser.add_argument("--max-chars", type=int, default=40_000, help="Max characters per document sent to LLM (default: 40000 ≈ 10k tokens)")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if args.manifest:
        archive_manifest_sources(Path(args.manifest), Path(args.archive_dir))
        source_dir = Path(args.archive_dir)

    if args.llm:
        from bottleneck_os.llm_extractor import extract_repository_from_directory
        repo = extract_repository_from_directory(
            source_dir,
            provider=args.provider,
            model=args.model,
            max_chars=args.max_chars,
        )
    else:
        from bottleneck_os.extractor import extract_repository_from_directory
        repo = extract_repository_from_directory(source_dir)

    status = "accepted" if args.auto_accept else "pending"
    documents_path, claims_path = write_review_artifacts(repo, Path(args.review_dir), default_status=status)
    print(f"documents={len(repo.documents)} claims={len(repo.claims)} status={status}")
    print(documents_path)
    print(claims_path)


if __name__ == "__main__":
    main()
