from __future__ import annotations

import unittest
from datetime import date

from bottleneck_os.reporting import evidence_gap_analysis, generate_run_report, source_coverage
from bottleneck_os.repository import build_seed_repository


class ReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = build_seed_repository()
        self.as_of = date(2026, 6, 10)

    def test_report_contains_results_gaps_sources_and_tests_section(self) -> None:
        report = generate_run_report(self.repo, self.as_of, "Ran 9 tests\nOK")
        self.assertIn("# Bottleneck OS Run Report", report)
        self.assertIn("## Bottleneck Results", report)
        self.assertIn("## Evidence Gap Analysis", report)
        self.assertIn("## Source Coverage", report)
        self.assertIn("## Technology Policy Coverage", report)
        self.assertIn("Ran 9 tests", report)

    def test_gap_analysis_shows_real_evidence_is_sufficient(self) -> None:
        gaps = {row["technology"]: row for row in evidence_gap_analysis(self.repo)}
        for technology in ["Power", "Cooling", "HBM", "Networking", "CPO"]:
            self.assertTrue(gaps[technology]["sufficient"])
            self.assertEqual([], gaps[technology]["missing"])

    def test_source_coverage_is_honest_about_real_data(self) -> None:
        coverage = {row["source"]: row for row in source_coverage(self.repo)}
        self.assertNotIn("seed://", coverage)
        self.assertEqual("present", coverage["Dylan Patel"]["status"])
        self.assertEqual("present", coverage["NVIDIA"]["status"])
        self.assertEqual("present", coverage["Micron"]["status"])


if __name__ == "__main__":
    unittest.main()
