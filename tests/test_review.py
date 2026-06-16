from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from bottleneck_os.extractor import extract_repository_from_directory
from bottleneck_os.review import (
    load_review_repository,
    review_summary,
    set_all_claim_statuses,
    update_claim_review,
    write_review_artifacts,
)
from bottleneck_os.scoring import technology_detail


class ReviewTests(unittest.TestCase):
    def test_pending_claims_are_not_used_for_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = sample_repo(Path(tmp))
            review_dir = Path(tmp) / "review"
            write_review_artifacts(repo, review_dir, default_status="pending")
            accepted_repo = load_review_repository(review_dir)
            self.assertEqual(0, len(accepted_repo.claims))
            detail = technology_detail(accepted_repo, "Power", date(2026, 6, 10))
            self.assertEqual("insufficient_evidence", detail["status"])

    def test_accepted_claims_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = sample_repo(Path(tmp))
            review_dir = Path(tmp) / "review"
            write_review_artifacts(repo, review_dir, default_status="pending")
            set_all_claim_statuses(review_dir, "accepted")
            accepted_repo = load_review_repository(review_dir)
            self.assertEqual(len(repo.claims), len(accepted_repo.claims))
            self.assertEqual({"accepted": len(repo.claims), "pending": 0, "rejected": 0}, review_summary(review_dir))

    def test_review_artifacts_are_jsonl_with_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = sample_repo(Path(tmp))
            review_dir = Path(tmp) / "review"
            _, claims_path = write_review_artifacts(repo, review_dir, default_status="pending")
            first = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual("pending", first["review_status"])
            self.assertIn("evidence_quote", first)

    def test_update_claim_review_changes_one_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = sample_repo(Path(tmp))
            review_dir = Path(tmp) / "review"
            _, claims_path = write_review_artifacts(repo, review_dir, default_status="pending")
            records = [json.loads(line) for line in claims_path.read_text(encoding="utf-8").splitlines()]
            updated = update_claim_review(review_dir, records[0]["id"], "accepted", "source checked")
            self.assertEqual("accepted", updated["review_status"])
            self.assertEqual("source checked", updated["reviewer_note"])
            summary = review_summary(review_dir)
            self.assertEqual(1, summary["accepted"])
            self.assertEqual(len(records) - 1, summary["pending"])

    def test_update_claim_review_rejects_invalid_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = sample_repo(Path(tmp))
            review_dir = Path(tmp) / "review"
            write_review_artifacts(repo, review_dir, default_status="pending")
            with self.assertRaises(ValueError):
                update_claim_review(review_dir, "claim_power_1", "approved")


def sample_repo(root: Path):
    source_dir = root / "sources"
    source_dir.mkdir()
    (source_dir / "power.md").write_text(
        "\n".join(
            [
                "title: Power Review Fixture",
                "source_name: NVIDIA",
                "source_type: technical_blog",
                "published_at: 2026-06-01",
                "url: https://example.com/power",
                "---",
                "NVIDIA says AI factories require new power architecture as rack power density rises.",
                "The grid and substation interconnection path can constrain deployment when demand grows.",
                "However, integrated rack design can reduce power connections and mitigate deployment complexity.",
            ]
        ),
        encoding="utf-8",
    )
    return extract_repository_from_directory(source_dir)


if __name__ == "__main__":
    unittest.main()
