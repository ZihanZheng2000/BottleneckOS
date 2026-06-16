from __future__ import annotations

import unittest

from bottleneck_os.expert_signal import (
    expert_signal_by_technology,
    expert_signal_summary,
    expert_source_coverage,
)
from bottleneck_os.repository import build_seed_repository


class ExpertSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = build_seed_repository()

    def test_expert_source_coverage_shows_present_and_missing_experts(self) -> None:
        rows = {row["source"]: row for row in expert_source_coverage(self.repo)}
        self.assertEqual("present", rows["Dylan Patel"]["status"])
        self.assertEqual("missing", rows["SemiAnalysis"]["status"])
        self.assertEqual("missing", rows["Serenity"]["status"])

    def test_expert_signal_by_technology_is_visible(self) -> None:
        rows = {row["technology"]: row for row in expert_signal_by_technology(self.repo)}
        self.assertEqual("present", rows["Power"]["status"])
        self.assertIn("Dylan Patel", rows["Power"]["expert_sources"])
        self.assertEqual("missing", rows["GPU"]["status"])

    def test_expert_signal_summary_counts_core_gaps(self) -> None:
        summary = expert_signal_summary(self.repo)
        self.assertEqual(1, summary["expert_sources_present"])
        self.assertIn("SemiAnalysis", summary["expert_sources_missing"])
        self.assertIn("GPU", summary["technologies_missing_expert_signal"])


if __name__ == "__main__":
    unittest.main()
