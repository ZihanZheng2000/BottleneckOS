from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from bottleneck_os.models import Claim, Document
from bottleneck_os.repository import Repository
from bottleneck_os.repository import build_seed_repository
from bottleneck_os.seed_data import TECHNOLOGIES
from bottleneck_os.storage import connect, persist_run
from bottleneck_os.trends import historical_trends, render_trends_markdown, write_trends_report


class TrendTests(unittest.TestCase):
    def test_trends_mark_insufficient_history_without_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "runs.sqlite")
            try:
                persist_run(conn, build_seed_repository(), date(2026, 6, 10), "full", run_id="full")
                rows = historical_trends(conn, date(2026, 6, 10))
                self.assertTrue(rows)
                self.assertTrue(all(row["30d_status"] == "insufficient_history" for row in rows))
                markdown = render_trends_markdown(rows, date(2026, 6, 10))
                self.assertIn("insufficient_history", markdown)
            finally:
                conn.close()

    def test_trends_calculate_delta_from_prior_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "runs.sqlite")
            try:
                persist_run(conn, small_power_repo(), date(2026, 6, 1), "small", run_id="small")
                persist_run(conn, build_seed_repository(), date(2026, 6, 10), "full", run_id="full")
                rows = {row["technology"]: row for row in historical_trends(conn, date(2026, 6, 10))}
                self.assertEqual("calculated", rows["Power"]["30d_status"])
                self.assertIsNotNone(rows["Power"]["30d_evidence_delta"])
                self.assertGreater(rows["Power"]["30d_evidence_delta"], 0)
            finally:
                conn.close()

    def test_write_trends_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = connect(root / "runs.sqlite")
            try:
                persist_run(conn, build_seed_repository(), date(2026, 6, 10), "full", run_id="full")
                path = write_trends_report(conn, date(2026, 6, 10), root / "trends.md")
                self.assertTrue(path.exists())
                self.assertIn("# Bottleneck OS Historical Trends", path.read_text(encoding="utf-8"))
            finally:
                conn.close()

    def test_trend_uses_newest_run_when_as_of_ties(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "runs.sqlite")
            try:
                persist_run(conn, small_power_repo(), date(2026, 6, 10), "small", run_id="aaa_small")
                persist_run(conn, build_seed_repository(), date(2026, 6, 10), "full", run_id="zzz_full")
                rows = {row["technology"]: row for row in historical_trends(conn, date(2026, 6, 10))}
                self.assertEqual(88, rows["Power"]["current_bottleneck_score"])
                self.assertEqual(4, rows["Power"]["current_evidence_count"])
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()


def small_power_repo() -> Repository:
    documents = [
        Document(
            "doc_small_power",
            "Small Power Fixture",
            "NVIDIA",
            "technical_blog",
            date(2026, 6, 1),
            "https://example.com/small-power",
            "NVIDIA says AI factories require new power architecture as rack power density rises.",
            0.9,
        )
    ]
    claims = [
        Claim(
            "claim_small_power",
            "doc_small_power",
            "tech_power",
            "technical_constraint",
            "AI factories require new power architecture as rack power density rises.",
            "NVIDIA says AI factories require new power architecture as rack power density rises.",
            0.78,
            78,
        )
    ]
    return Repository(list(TECHNOLOGIES), documents, claims)
