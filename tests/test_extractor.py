from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bottleneck_os.extractor import extract_document_and_claims, extract_repository_from_directory


class ExtractorTests(unittest.TestCase):
    def test_extracts_document_and_claims_from_source_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nvidia_power.md"
            path.write_text(
                "\n".join(
                    [
                        "title: Test NVIDIA Power Source",
                        "source_name: NVIDIA",
                        "source_type: technical_blog",
                        "published_at: 2026-06-01",
                        "url: https://example.com/nvidia-power",
                        "reliability_weight: 0.9",
                        "---",
                        "NVIDIA says AI factories require new power architecture as rack power density rises.",
                        "However, integrated rack design can reduce power connections and mitigate deployment complexity.",
                    ]
                ),
                encoding="utf-8",
            )
            document, claims = extract_document_and_claims(path)
            self.assertEqual("NVIDIA", document.source_name)
            self.assertGreaterEqual(len(claims), 2)
            self.assertTrue(any(claim.technology_id == "tech_power" for claim in claims))
            self.assertTrue(any(claim.claim_type == "counterargument" for claim in claims))

    def test_extracts_repository_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text("# Instructions\n", encoding="utf-8")
            path = Path(tmp) / "arista_networking.md"
            path.write_text(
                "\n".join(
                    [
                        "title: Test Arista Networking Source",
                        "source_name: Arista",
                        "source_type: whitepaper",
                        "published_at: 2026-06-10",
                        "url: https://example.com/arista-networking",
                        "---",
                        "AI networking demand is expanding as Ethernet clusters scale to large accelerator deployments.",
                        "These clusters create bandwidth, latency, space, and power consumption constraints.",
                    ]
                ),
                encoding="utf-8",
            )
            repo = extract_repository_from_directory(Path(tmp))
            self.assertEqual(1, len(repo.documents))
            self.assertGreaterEqual(len(repo.claims), 2)


if __name__ == "__main__":
    unittest.main()
