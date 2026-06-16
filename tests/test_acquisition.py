from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from bottleneck_os.acquisition import build_acquisition_plan, render_acquisition_plan, write_acquisition_plan
from bottleneck_os.repository import build_seed_repository


class AcquisitionPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = build_seed_repository()

    def test_plan_targets_missing_core_technologies(self) -> None:
        plan = {item["technology"]: item for item in build_acquisition_plan(self.repo)}
        self.assertIn("GPU", plan)
        self.assertIn("CoWoS", plan)
        self.assertIn("Switch ASIC", plan)
        self.assertNotIn("HBM", plan)
        self.assertEqual(3, plan["GPU"]["minimum_new_evidence_items"])
        self.assertTrue(plan["GPU"]["candidate_sources"])

    def test_plan_uses_public_source_targets_without_fabricating_urls(self) -> None:
        plan = {item["technology"]: item for item in build_acquisition_plan(self.repo)}
        gpu_sources = {source["name"] for source in plan["GPU"]["candidate_sources"]}
        self.assertIn("NVIDIA", gpu_sources)
        self.assertIn("Dylan Patel", gpu_sources)
        rendered = render_acquisition_plan(list(plan.values()), date(2026, 6, 10))
        self.assertIn("This report is a collection plan, not evidence", rendered)
        self.assertIn('NVIDIA "GPU" AI infrastructure bottleneck', rendered)
        self.assertNotIn("latest", rendered.lower())

    def test_plan_prioritizes_expert_sources_for_all_gaps(self) -> None:
        plan = {item["technology"]: item for item in build_acquisition_plan(self.repo)}
        for technology in ["Switch ASIC", "Optical Transceiver", "Transformer", "Rack Density"]:
            sources = {source["name"] for source in plan[technology]["candidate_sources"]}
            self.assertIn("Dylan Patel", sources)
            self.assertIn("SemiAnalysis", sources)

    def test_write_acquisition_plan_creates_dated_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "2026-06-10_acquisition_plan.md"
            path = write_acquisition_plan(self.repo, date(2026, 6, 10), output)
            self.assertTrue(path.exists())
            self.assertIn("Generated as of: 2026-06-10", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
