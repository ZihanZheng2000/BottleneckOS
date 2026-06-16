from __future__ import annotations

import unittest

from bottleneck_os.schemas import validate_claim_record, validate_claim_records, validate_document_record


class SchemaTests(unittest.TestCase):
    def test_valid_document_and_claim_records(self) -> None:
        document = valid_document()
        claim = valid_claim()
        self.assertEqual([], validate_document_record(document))
        self.assertEqual([], validate_claim_record(claim))
        self.assertEqual([], validate_claim_records([claim], {document["id"]}))

    def test_invalid_claim_type_confidence_and_doc_reference_are_reported(self) -> None:
        claim = valid_claim()
        claim["claim_type"] = "vibes"
        claim["confidence"] = 1.5
        errors = validate_claim_records([claim], {"other_doc"})
        joined = "\n".join(errors)
        self.assertIn("claim_type invalid", joined)
        self.assertIn("confidence must be between 0 and 1", joined)
        self.assertIn("doc_id has no matching document", joined)

    def test_invalid_document_url_date_and_weight_are_reported(self) -> None:
        document = valid_document()
        document["url"] = "ftp://example.com"
        document["published_at"] = "06/10/2026"
        document["reliability_weight"] = 3
        errors = validate_document_record(document)
        joined = "\n".join(errors)
        self.assertIn("url must start", joined)
        self.assertIn("must be ISO date", joined)
        self.assertIn("reliability_weight must be between 0 and 1", joined)


def valid_document() -> dict:
    return {
        "id": "doc_1",
        "title": "Source",
        "source_name": "NVIDIA",
        "source_type": "technical_blog",
        "published_at": "2026-06-10",
        "url": "https://example.com/source",
        "clean_text": "NVIDIA says AI factories require new power architecture.",
        "reliability_weight": 0.9,
    }


def valid_claim() -> dict:
    return {
        "id": "claim_1",
        "doc_id": "doc_1",
        "technology_id": "tech_power",
        "claim_type": "technical_constraint",
        "claim": "AI factories require new power architecture.",
        "evidence_quote": "NVIDIA says AI factories require new power architecture.",
        "confidence": 0.8,
        "impact": 80,
        "review_status": "accepted",
        "reviewer_note": "",
    }


if __name__ == "__main__":
    unittest.main()
