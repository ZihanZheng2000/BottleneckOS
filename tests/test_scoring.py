from __future__ import annotations

import unittest
from datetime import date

from bottleneck_os.repository import build_seed_repository
from bottleneck_os.scoring import (
    bottleneck_radar,
    bottleneck_score,
    evidence_is_sufficient,
    technology_detail,
    technology_radar,
)
from bottleneck_os.thesis import generate_thesis


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = build_seed_repository()
        self.as_of = date(2026, 6, 10)

    def test_power_has_sufficient_evidence_and_score(self) -> None:
        tech = self.repo.technology_by_name("Power")
        self.assertTrue(evidence_is_sufficient(self.repo, tech.id))
        self.assertGreaterEqual(bottleneck_score(self.repo, tech.id) or 0, 80)

    def test_hbm_is_precisely_scored_with_real_multisource_evidence(self) -> None:
        tech = self.repo.technology_by_name("HBM")
        self.assertTrue(evidence_is_sufficient(self.repo, tech.id))
        self.assertGreaterEqual(bottleneck_score(self.repo, tech.id) or 0, 65)

    def test_radar_contracts(self) -> None:
        tech_radar = technology_radar(self.repo, self.as_of)
        bottlenecks = bottleneck_radar(self.repo, self.as_of)
        self.assertEqual({"current", "emerging", "declining", "insufficient_evidence"}, set(bottlenecks))
        self.assertGreaterEqual(len(tech_radar), 11)
        self.assertEqual("Power", bottlenecks["current"][0]["technology"])
        self.assertEqual(5, len(bottlenecks["current"]))
        insufficient = {item["technology"] for item in bottlenecks["insufficient_evidence"]}
        self.assertEqual(
            {"GPU", "CoWoS", "Switch ASIC", "Optical Transceiver", "Transformer", "Rack Density"},
            insufficient,
        )

    def test_detail_contains_breakdown_evidence_and_counterarguments(self) -> None:
        detail = technology_detail(self.repo, "Cooling", self.as_of)
        self.assertEqual("Cooling", detail["technology"])
        self.assertIn("demand_growth", detail["breakdown"])
        self.assertGreaterEqual(len(detail["evidence"]), 3)
        self.assertGreaterEqual(len(detail["counterarguments"]), 1)

    def test_thesis_is_markdown_and_evidence_backed(self) -> None:
        thesis = generate_thesis(self.repo, "Power", self.as_of)
        self.assertTrue(thesis.startswith("# Bottleneck Thesis: Power"))
        self.assertIn("## Key Evidence", thesis)
        self.assertIn("## Counterarguments", thesis)


if __name__ == "__main__":
    unittest.main()
