"""Command-line entry point."""

from __future__ import annotations

import argparse

from .api import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Bottleneck OS MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--review-dir", default=None, help="Load claims from review artifacts instead of seed data")
    args = parser.parse_args()
    run(args.host, args.port, review_dir=args.review_dir)


if __name__ == "__main__":
    main()
