from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from bottleneck_os.diffing import compare_runs, render_diff_markdown, write_diff_report
from bottleneck_os.models import Claim, Document
from bottleneck_os.repository import Repository, build_seed_repository
from bottleneck_os.seed_data import TECHNOLOGIES
from bottleneck_os.storage import connect, persist_run


class DiffingTests(unittest.TestCase):
    def test_compare_runs_reports_score_and_coverage_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "runs.sqlite")
            try:
                full_repo = build_seed_repository()
                small_repo = small_power_repo()
                persist_run(conn, small_repo, date(2026, 6, 1), "small", run_id="small")
                persist_run(conn, full_repo, date(2026, 6, 10), "full", run_id="full")
                diff = compare_runs(conn, "small", "full")
                rows = {row["technology"]: row for row in diff["score_deltas"]}
                self.assertIn("HBM", rows)
                self.assertEqual("changed", rows["HBM"]["status"])
                self.assertGreater(rows["HBM"]["evidence_delta"], 0)
                self.assertGreater(
                    diff["coverage"]["current"]["core_sources_present"],
                    diff["coverage"]["base"]["core_sources_present"],
                )
                markdown = render_diff_markdown(diff)
                self.assertIn("# Bottleneck OS Run Diff", markdown)
                self.assertIn("Core technologies covered", markdown)
            finally:
                conn.close()

    def test_write_diff_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = connect(root / "runs.sqlite")
            try:
                persist_run(conn, small_power_repo(), date(2026, 6, 1), "small", run_id="small")
                persist_run(conn, build_seed_repository(), date(2026, 6, 10), "full", run_id="full")
                path = write_diff_report(conn, "small", "full", root / "diff.md")
                self.assertTrue(path.exists())
                self.assertIn("Missing core sources", path.read_text(encoding="utf-8"))
            finally:
                conn.close()


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


if __name__ == "__main__":
    unittest.main()
