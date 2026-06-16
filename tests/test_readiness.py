from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from bottleneck_os.readiness import run_readiness_audit, write_readiness_report
from bottleneck_os.repository import build_seed_repository
from bottleneck_os.review import write_review_artifacts
from bottleneck_os.storage import connect, persist_run


class ReadinessTests(unittest.TestCase):
    def test_readiness_audit_passes_with_warnings_for_known_coverage_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_minimum_artifacts(root)
            audit = run_readiness_audit(root, "2026-06-10")
            self.assertEqual("ready_with_warnings", audit["status"])
            self.assertFalse(audit["errors"])
            self.assertTrue(any(check.name == "coverage" and check.status == "warning" for check in audit["warnings"]))
            path = write_readiness_report(audit, "2026-06-10", root / "reports" / "audit.md")
            self.assertIn("Production Readiness Audit", path.read_text(encoding="utf-8"))

    def test_readiness_audit_errors_without_test_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_minimum_artifacts(root, include_tests=False)
            audit = run_readiness_audit(root, "2026-06-10")
            self.assertEqual("not_ready", audit["status"])
            self.assertTrue(any(check.name == "tests" for check in audit["errors"]))

    def test_readiness_audit_errors_on_invalid_review_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_minimum_artifacts(root)
            claims_path = root / "review" / "current" / "claims.jsonl"
            records = [json.loads(line) for line in claims_path.read_text(encoding="utf-8").splitlines() if line]
            records[0]["confidence"] = 9.0
            claims_path.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")
            audit = run_readiness_audit(root, "2026-06-10")
            self.assertEqual("not_ready", audit["status"])
            self.assertTrue(any(check.name == "review" for check in audit["errors"]))

    def test_readiness_audit_errors_when_evidence_quote_is_not_traceable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_minimum_artifacts(root)
            claims_path = root / "review" / "current" / "claims.jsonl"
            records = [json.loads(line) for line in claims_path.read_text(encoding="utf-8").splitlines() if line]
            records[0]["evidence_quote"] = "This sentence is not in the stored source text."
            claims_path.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")
            audit = run_readiness_audit(root, "2026-06-10")
            self.assertEqual("not_ready", audit["status"])
            self.assertTrue(any(check.name == "evidence" for check in audit["errors"]))


def make_minimum_artifacts(root: Path, include_tests: bool = True) -> None:
    reports = root / "reports"
    reports.mkdir()
    for name in [
        "2026-06-10_report.md",
        "2026-06-10_historical_trends.md",
        "2026-06-10_run_diff.md",
        "2026-06-10_acquisition_plan.md",
    ]:
        (reports / name).write_text("# report\n", encoding="utf-8")
    if include_tests:
        (reports / "2026-06-10_test-results.txt").write_text("Ran 1 test\n\nOK\n", encoding="utf-8")

    archive = root / "archive" / "sources"
    archive.mkdir(parents=True)
    (archive / "source.md").write_text("title: Source\n---\nBody\n", encoding="utf-8")
    (archive / "source.raw").write_text("Body\n", encoding="utf-8")

    repo = build_seed_repository()
    write_review_artifacts(repo, root / "review" / "current", default_status="accepted")

    conn = connect(root / "data" / "bottleneck_os.sqlite")
    try:
        persist_run(conn, repo, date(2026, 6, 10), "seed", run_id="seed")
    finally:
        conn.close()


if __name__ == "__main__":
    unittest.main()
