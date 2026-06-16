from __future__ import annotations

import unittest

from bottleneck_os.coverage import coverage_summary, source_coverage, technology_policy_coverage
from bottleneck_os.repository import build_seed_repository


class CoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = build_seed_repository()

    def test_source_policy_reports_present_and_missing_core_sources(self) -> None:
        rows = {row["source"]: row for row in source_coverage(self.repo)}
        self.assertEqual("present", rows["NVIDIA"]["status"])
        self.assertEqual("present", rows["Dylan Patel"]["status"])
        self.assertEqual("missing", rows["SemiAnalysis"]["status"])
        self.assertEqual("core", rows["SemiAnalysis"]["priority"])

    def test_technology_policy_shows_mvp_coverage_gap(self) -> None:
        rows = {row["technology"]: row for row in technology_policy_coverage(self.repo)}
        self.assertEqual("covered", rows["HBM"]["status"])
        self.assertEqual("covered", rows["Power"]["status"])
        self.assertEqual("missing", rows["GPU"]["status"])
        self.assertEqual("core", rows["GPU"]["priority"])
        self.assertEqual("partial", rows["CoWoS"]["status"])
        self.assertEqual("partial", rows["Rack Density"]["status"])

    def test_coverage_summary_counts_core_universe(self) -> None:
        summary = coverage_summary(self.repo)
        self.assertGreater(summary["core_sources_total"], summary["core_sources_present"])
        self.assertIn("SemiAnalysis", summary["core_sources_missing"])
        self.assertIn("GPU", summary["core_technologies_missing"])
        self.assertIn("CoWoS", summary["core_technologies_partial"])


if __name__ == "__main__":
    unittest.main()
