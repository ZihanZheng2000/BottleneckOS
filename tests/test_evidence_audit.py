from __future__ import annotations

import unittest

from bottleneck_os.evidence_audit import audit_evidence_traceability
from bottleneck_os.models import Claim, Document, Technology
from bottleneck_os.repository import Repository, build_seed_repository


class EvidenceAuditTests(unittest.TestCase):
    def test_seed_repository_claims_trace_to_public_source_text(self) -> None:
        audit = audit_evidence_traceability(build_seed_repository())
        self.assertEqual([], audit["errors"])
        self.assertEqual("pass", audit["status"])

    def test_audit_fails_when_quote_is_not_in_document(self) -> None:
        technology = Technology("tech_power", "Power", "Power")
        document = Document(
            "doc_power",
            "Power report",
            "NVIDIA",
            "technical_blog",
            __import__("datetime").date(2026, 1, 1),
            "https://example.org/power",
            "The grid connection queue is lengthening for AI data centers.",
            0.9,
        )
        claim = Claim(
            "claim_power",
            "doc_power",
            "tech_power",
            "infrastructure_constraint",
            "AI data centers face grid constraints.",
            "This quote is not in the source document.",
            0.9,
            80,
        )
        audit = audit_evidence_traceability(Repository([technology], [document], [claim]))
        self.assertEqual("fail", audit["status"])
        self.assertTrue(audit["errors"])


if __name__ == "__main__":
    unittest.main()
