from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from bottleneck_os.api import BottleneckHandler
from bottleneck_os.repository import build_seed_repository
from bottleneck_os.review import write_review_artifacts


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.review_dir = Path(cls.tempdir.name) / "review"
        write_review_artifacts(build_seed_repository(), cls.review_dir, default_status="pending")
        BottleneckHandler.review_dir = cls.review_dir
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), BottleneckHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.tempdir.cleanup()

    def get_json(self, path: str) -> dict | list:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
        self.assertEqual(200, response.status, body)
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
