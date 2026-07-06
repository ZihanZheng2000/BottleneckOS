from __future__ import annotations

import unittest
from datetime import date

import bottleneck_os.scoring as scoring_module
from bottleneck_os.repository import Repository, build_seed_repository
from bottleneck_os.scoring import (
    bottleneck_radar,
    bottleneck_score,
    evidence_is_sufficient,
    score_snapshots,
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
        self.assertTrue(all("interpretation" in row for row in tech_radar))
        self.assertTrue(all("growth_30d_label" in row for row in tech_radar))
        self.assertEqual("Power", bottlenecks["current"][0]["technology"])
        self.assertEqual(5, len(bottlenecks["current"]))
        insufficient = {item["technology"] for item in bottlenecks["insufficient_evidence"]}
        self.assertEqual(
            {"GPU", "CoWoS", "Switch ASIC", "Optical Transceiver", "Transformer", "Rack Density"},
            insufficient,
        )

    def test_technology_radar_does_not_overstate_low_evidence_as_momentum(self) -> None:
        rows = {row["technology"]: row for row in technology_radar(self.repo, self.as_of)}
        self.assertEqual("low evidence", rows["GPU"]["momentum"])
        self.assertEqual("n/a", rows["GPU"]["growth_30d_label"])
        self.assertIn("not that the technology is irrelevant", rows["GPU"]["interpretation"])
        self.assertEqual("insufficient history", rows["Power"]["growth_30d_label"])

    def test_detail_contains_breakdown_evidence_and_counterarguments(self) -> None:
        detail = technology_detail(self.repo, "Cooling", self.as_of)
        self.assertEqual("Cooling", detail["technology"])
        self.assertIn("demand_growth", detail["breakdown"])
        self.assertGreaterEqual(len(detail["evidence"]), 3)
        self.assertGreaterEqual(len(detail["counterarguments"]), 1)

    def test_score_snapshots_are_cached_per_repo_version_and_as_of(self) -> None:
        calls: list[date] = []
        original = scoring_module._compute_score_snapshots

        def counting_wrapper(repo, as_of):
            calls.append(as_of)
            return original(repo, as_of)

        scoring_module._compute_score_snapshots = counting_wrapper
        try:
            first = score_snapshots(self.repo, self.as_of)
            second = score_snapshots(self.repo, self.as_of)
            self.assertEqual(1, len(calls), "second call with the same repo+as_of should hit the cache")
            self.assertEqual(first, second)

            # A structurally-identical but distinct Repository instance (e.g. after
            # an ingest) must NOT reuse the first repo's cached entry.
            other_repo = Repository(list(self.repo.technologies), list(self.repo.documents), list(self.repo.claims))
            score_snapshots(other_repo, self.as_of)
            self.assertEqual(2, len(calls), "a different repo instance must miss the cache")

            score_snapshots(self.repo, date(2026, 6, 11))
            self.assertEqual(3, len(calls), "a different as_of must miss the cache")
        finally:
            scoring_module._compute_score_snapshots = original

    def test_thesis_is_markdown_and_evidence_backed(self) -> None:
        thesis = generate_thesis(self.repo, "Power", self.as_of)
        self.assertTrue(thesis.startswith("# Bottleneck Thesis: Power"))
        self.assertIn("## Key Evidence", thesis)
        self.assertIn("## Counterarguments", thesis)


if __name__ == "__main__":
    unittest.main()
