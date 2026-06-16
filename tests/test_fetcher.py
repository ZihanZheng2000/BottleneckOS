from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bottleneck_os.fetcher import archive_manifest_sources, parse_manifest, source_text_for_item


class FetcherTests(unittest.TestCase):
    def test_parse_manifest_multiple_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.txt"
            manifest.write_text(
                "\n".join(
                    [
                        "title: One",
                        "source_name: NVIDIA",
                        "source_type: technical_blog",
                        "published_at: 2026-01-01",
                        "url: https://example.com/one",
                        "---",
                        "title: Two",
                        "source_name: Micron",
                        "source_type: press_release",
                        "published_at: 2026-01-02",
                        "url: https://example.com/two",
                    ]
                ),
                encoding="utf-8",
            )
            items = parse_manifest(manifest)
            self.assertEqual(2, len(items))
            self.assertEqual("NVIDIA", items[0].source_name)
            self.assertEqual("Micron", items[1].source_name)

    def test_archive_local_file_manifest_to_source_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text(
                "NVIDIA AI factories require power architecture as rack power density rises.",
                encoding="utf-8",
            )
            manifest = root / "manifest.txt"
            manifest.write_text(
                "\n".join(
                    [
                        "title: Local NVIDIA Source",
                        "source_name: NVIDIA",
                        "source_type: technical_blog",
                        "published_at: 2026-06-01",
                        f"url: file://{source}",
                        "reliability_weight: 0.9",
                    ]
                ),
                encoding="utf-8",
            )
            archive = root / "archive"
            paths = archive_manifest_sources(manifest, archive)
            self.assertEqual(1, len(paths))
            archived = paths[0].read_text(encoding="utf-8")
            self.assertIn("fetch_status: fetched", archived)
            self.assertIn("content_kind: text", archived)
            self.assertIn("rack power density", archived)
            self.assertEqual(1, len(list(archive.glob("*.raw"))))

    def test_archive_strips_existing_source_header_from_text_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.md"
            source.write_text(
                "\n".join(
                    [
                        "title: Inner Header",
                        "source_name: Inner",
                        "---",
                        "NVIDIA AI factories require power architecture as rack power density rises.",
                    ]
                ),
                encoding="utf-8",
            )
            manifest = root / "manifest.txt"
            manifest.write_text(
                "\n".join(
                    [
                        "title: Outer Source",
                        "source_name: NVIDIA",
                        "source_type: technical_blog",
                        "published_at: 2026-06-01",
                        f"url: file://{source}",
                    ]
                ),
                encoding="utf-8",
            )
            archived_path = archive_manifest_sources(manifest, root / "archive")[0]
            archived = archived_path.read_text(encoding="utf-8")
            body = archived.split("---", 1)[1]
            self.assertNotIn("Inner Header", body)
            self.assertIn("rack power density rises", body)

    def test_pdf_is_marked_unsupported_instead_of_fake_parsed(self) -> None:
        item = parse_manifest_text(
            "\n".join(
                [
                    "title: PDF",
                    "source_name: Test",
                    "source_type: report",
                    "published_at: 2026-01-01",
                    "url: https://example.com/file.pdf",
                ]
            )
        )
        kind, body = source_text_for_item(item, b"%PDF-1.4 bytes", "application/pdf")
        self.assertEqual("unsupported_pdf", kind)
        self.assertIn("not parsed", body)


def parse_manifest_text(text: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "manifest.txt"
        path.write_text(text, encoding="utf-8")
        return parse_manifest(path)[0]


if __name__ == "__main__":
    unittest.main()
