from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, timedelta
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from bottleneck_os.api import BottleneckHandler
from bottleneck_os.repository import build_seed_repository
from bottleneck_os.review import write_review_artifacts
from bottleneck_os.storage import connect, persist_run


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.review_dir = Path(cls.tempdir.name) / "review"
        write_review_artifacts(build_seed_repository(), cls.review_dir, default_status="pending")
        BottleneckHandler.review_dir = cls.review_dir

        cls.db_path = Path(cls.tempdir.name) / "bottleneck_os.sqlite"
        BottleneckHandler.db_path = cls.db_path
        conn = connect(cls.db_path)
        repo = build_seed_repository()
        persist_run(conn, repo, date.today() - timedelta(days=20), "test-baseline")
        persist_run(conn, repo, date.today(), "test-current")
        conn.close()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), BottleneckHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.tempdir.cleanup()

    def get_json(self, path: str, expected_status: int = 200) -> dict | list:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
        self.assertEqual(expected_status, response.status, body)
        return json.loads(body)

    def post_json(self, path: str, payload: dict, expected_status: int = 200) -> dict | list:
        body = json.dumps(payload)
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        response_body = response.read().decode("utf-8")
        conn.close()
        self.assertEqual(expected_status, response.status, response_body)
        return json.loads(response_body)

    def test_health(self) -> None:
        payload = self.get_json("/api/health")
        self.assertEqual(True, payload["ok"])

    def test_bottleneck_endpoint(self) -> None:
        payload = self.get_json("/api/bottlenecks/Power")
        self.assertEqual("Power", payload["technology"])
        self.assertGreaterEqual(payload["score"], 80)

    def test_thesis_endpoint(self) -> None:
        payload = self.get_json("/api/theses?technology=Power")
        self.assertEqual("Power", payload["technology"])
        self.assertIn("# Bottleneck Thesis: Power", payload["markdown"])

    def test_coverage_endpoint(self) -> None:
        payload = self.get_json("/api/coverage")
        self.assertIn("summary", payload)
        self.assertIn("sources", payload)
        self.assertIn("technologies", payload)
        self.assertIn("SemiAnalysis", payload["summary"]["core_sources_missing"])
        self.assertIn("GPU", payload["summary"]["core_technologies_missing"])

    def test_evidence_audit_endpoint(self) -> None:
        payload = self.get_json("/api/evidence-audit")
        self.assertEqual("pass", payload["status"])
        self.assertEqual([], payload["errors"])
        self.assertGreater(payload["claims_checked"], 0)

    def test_policy_endpoints(self) -> None:
        sources = self.get_json("/api/policy/sources")
        technologies = self.get_json("/api/policy/technologies")
        self.assertTrue(any(item["name"] == "NVIDIA" for item in sources))
        self.assertTrue(any(item["name"] == "GPU" for item in technologies))

    def test_acquisition_plan_endpoint(self) -> None:
        payload = self.get_json("/api/acquisition-plan")
        technologies = {item["technology"] for item in payload["items"]}
        self.assertRegex(payload["as_of"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("GPU", technologies)
        self.assertIn("CoWoS", technologies)

    def test_expert_signal_endpoint(self) -> None:
        payload = self.get_json("/api/expert-signal")
        self.assertIn("summary", payload)
        self.assertIn("sources", payload)
        self.assertIn("technologies", payload)
        sources = {item["source"]: item for item in payload["sources"]}
        self.assertEqual("present", sources["Dylan Patel"]["status"])
        self.assertEqual("missing", sources["SemiAnalysis"]["status"])

    def test_runs_endpoint(self) -> None:
        payload = self.get_json("/api/runs")
        run_ids = {row["run_id"] for row in payload["runs"]}
        self.assertGreaterEqual(len(run_ids), 2)
        self.assertTrue(any(row["source"] == "test-current" for row in payload["runs"]))

    def test_trends_endpoint(self) -> None:
        payload = self.get_json("/api/trends")
        self.assertRegex(payload["as_of"], r"^\d{4}-\d{2}-\d{2}$")
        row = next(item for item in payload["technologies"] if item["technology"] == "Power")
        self.assertEqual("calculated", row["30d_status"])
        self.assertEqual(0, row["30d_score_delta"])

    def test_run_diff_endpoint(self) -> None:
        payload = self.get_json("/api/run-diff")
        self.assertIn("score_deltas", payload)
        self.assertIn("base", payload)
        self.assertIn("current", payload)

    def test_run_diff_endpoint_rejects_unknown_run(self) -> None:
        payload = self.get_json("/api/run-diff?base_run=missing&current_run=also-missing", expected_status=404)
        self.assertIn("Unknown run_id", payload["error"])

    def test_ingest_endpoint_extracts_claims_from_text(self) -> None:
        payload = self.post_json(
            "/api/ingest",
            {
                "text": (
                    "GPU demand is surging as hyperscalers scale accelerator deployments, "
                    "however supply is expected to improve as new fabs ramp."
                ),
                "source_name": "ingest-test-source",
                "title": "Ingest test document",
                "use_llm": False,
            },
        )
        self.assertIn("document_id", payload)
        self.assertIn("llm_error", payload)
        self.assertGreaterEqual(payload["claims_extracted"], 0)

    def test_ingest_endpoint_rejects_duplicate_document(self) -> None:
        body = {
            "text": "Cooling systems face new thermal density constraints in AI data centers.",
            "source_name": "duplicate-test-source",
            "title": "Duplicate test document",
            "use_llm": False,
        }
        self.post_json("/api/ingest", body)
        payload = self.post_json("/api/ingest", body, expected_status=400)
        self.assertIn("already been ingested", payload["error"])

    def test_ingest_endpoint_reports_llm_fallback_reason(self) -> None:
        import bottleneck_os.llm_extractor as llm_extractor_module

        original = llm_extractor_module.detect_provider

        def failing_detect_provider(preferred: str = "auto"):
            raise RuntimeError("no key configured for test")

        llm_extractor_module.detect_provider = failing_detect_provider
        try:
            payload = self.post_json(
                "/api/ingest",
                {
                    "text": "Networking switch ASIC supply is constrained by advanced packaging capacity.",
                    "source_name": "llm-fallback-test-source",
                    "title": "LLM fallback test document",
                },
            )
        finally:
            llm_extractor_module.detect_provider = original
        self.assertEqual("keyword", payload["extraction_method"])
        self.assertIn("no key configured for test", payload["llm_error"])

    def test_ingest_endpoint_rejects_local_file_url(self) -> None:
        payload = self.post_json(
            "/api/ingest", {"url": "file:///etc/passwd"}, expected_status=400,
        )
        self.assertIn("Unsupported URL scheme", payload["error"])

    def test_ingest_endpoint_rejects_private_network_url(self) -> None:
        payload = self.post_json(
            "/api/ingest", {"url": "http://169.254.169.254/latest/meta-data/"}, expected_status=400,
        )
        self.assertIn("non-public address", payload["error"])

    def test_review_endpoint(self) -> None:
        payload = self.get_json("/api/review")
        self.assertIn("summary", payload)
        self.assertIn("claims", payload)
        self.assertEqual({"accepted", "pending", "rejected"}, set(payload["summary"]))

    def test_review_claim_update_endpoint(self) -> None:
        review = self.get_json("/api/review")
        claim_id = review["claims"][0]["id"]
        payload = self.post_json(
            f"/api/review/claims/{claim_id}",
            {"review_status": "accepted", "reviewer_note": "checked in API test"},
        )
        self.assertEqual("accepted", payload["claim"]["review_status"])
        self.assertEqual("checked in API test", payload["claim"]["reviewer_note"])
        self.assertEqual(1, payload["summary"]["accepted"])

    def test_review_claim_update_rejects_invalid_status(self) -> None:
        payload = self.post_json(
            "/api/review/claims/missing",
            {"review_status": "approved"},
            expected_status=400,
        )
        self.assertIn("Invalid review status", payload["error"])


if __name__ == "__main__":
    unittest.main()
