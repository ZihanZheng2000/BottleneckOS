"""Manual-trigger source fetching and local archiving.

The fetcher turns a small manifest into archived Markdown source files that the
existing extractor can process. It is intentionally conservative: HTML pages are
cleaned with standard-library tools, text files are copied, and binary/PDF
assets are archived as unsupported text extraction candidates instead of being
silently mis-parsed.
"""

from __future__ import annotations

import hashlib
import html
import re
import shutil
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ManifestItem:
    title: str
    source_name: str
    source_type: str
    published_at: str
    url: str
    reliability_weight: str = "0.8"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip = True
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip = False
        if tag in {"p", "div", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            stripped = data.strip()
            if stripped:
                self.parts.append(stripped)

    def text(self) -> str:
        return clean_text(" ".join(self.parts))


def clean_text(text: str) -> str:
    unescaped = html.unescape(text)
    unescaped = re.sub(r"\s+", " ", unescaped)
    unescaped = re.sub(r"\s+([,.!?;:])", r"\1", unescaped)
    return unescaped.strip()


def strip_source_header(text: str) -> str:
    lines = text.splitlines()
    header_like = False
    for line in lines[:8]:
        if line.strip() == "---":
            header_like = True
            break
        if ":" not in line and line.strip():
            return text
    if not header_like:
        return text
    for index, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return text


def html_to_text(content: str) -> str:
    parser = _TextExtractor()
    parser.feed(content)
    return parser.text()


def parse_manifest(path: Path) -> list[ManifestItem]:
    items: list[ManifestItem] = []
    current: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "---":
            if current:
                items.append(_manifest_item(current))
                current = {}
            continue
        if ":" not in line:
            raise ValueError(f"Invalid manifest line: {raw_line}")
        key, value = line.split(":", 1)
        current[key.strip().lower()] = value.strip()
    if current:
        items.append(_manifest_item(current))
    return items


def _manifest_item(data: dict[str, str]) -> ManifestItem:
    required = ["title", "source_name", "source_type", "published_at", "url"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Manifest item missing required keys: {', '.join(missing)}")
    return ManifestItem(
        data["title"],
        data["source_name"],
        data["source_type"],
        data["published_at"],
        data["url"],
        data.get("reliability_weight", "0.8"),
    )


def fetch_url(url: str, timeout: int = 20, user_agent: str = "BottleneckOS/0.1 research fetcher") -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        return response.read(), content_type


def source_text_for_item(item: ManifestItem, fetched: bytes, content_type: str) -> tuple[str, str]:
    parsed = urlparse(item.url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix == ".pdf" or "application/pdf" in content_type.lower():
        return (
            "unsupported_pdf",
            "PDF content was archived but not parsed by the dependency-free fetcher. "
            "Add extracted text manually or enable a PDF parser in the production pipeline.",
        )
    try:
        decoded = fetched.decode("utf-8")
    except UnicodeDecodeError:
        decoded = fetched.decode("latin-1", errors="replace")
    if "html" in content_type.lower() or "<html" in decoded[:1000].lower():
        return "html", html_to_text(decoded)
    return "text", clean_text(strip_source_header(decoded))


def archive_manifest_sources(manifest_path: Path, archive_dir: Path, timeout: int = 20) -> list[Path]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_paths: list[Path] = []
    for item in parse_manifest(manifest_path):
        digest = hashlib.sha1(item.url.encode("utf-8")).hexdigest()[:12]
        safe_source = re.sub(r"[^A-Za-z0-9]+", "_", item.source_name).strip("_").lower()
        output_path = archive_dir / f"{item.published_at}_{safe_source}_{digest}.md"
        status = "fetched"
        content_kind = "unknown"
        body = ""
        raw_archive = archive_dir / f"{item.published_at}_{safe_source}_{digest}.raw"
        try:
            if item.url.startswith("file://"):
                local_path = Path(item.url.removeprefix("file://"))
                fetched = local_path.read_bytes()
                content_type = "text/plain" if local_path.suffix.lower() in {".txt", ".md"} else ""
            else:
                fetched, content_type = fetch_url(item.url, timeout=timeout)
            raw_archive.write_bytes(fetched)
            content_kind, body = source_text_for_item(item, fetched, content_type)
        except Exception as exc:  # noqa: BLE001 - archive failure reason for auditability.
            status = "fetch_failed"
            body = f"Fetch failed: {type(exc).__name__}: {exc}"
        output_path.write_text(render_source_markdown(item, status, content_kind, body), encoding="utf-8")
        archived_paths.append(output_path)
    return archived_paths


def render_source_markdown(item: ManifestItem, status: str, content_kind: str, body: str) -> str:
    return "\n".join(
        [
            f"title: {item.title}",
            f"source_name: {item.source_name}",
            f"source_type: {item.source_type}",
            f"published_at: {item.published_at}",
            f"url: {item.url}",
            f"reliability_weight: {item.reliability_weight}",
            f"fetch_status: {status}",
            f"content_kind: {content_kind}",
            "---",
            body.strip(),
            "",
        ]
    )


def copy_text_sources(source_dir: Path, archive_dir: Path) -> list[Path]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in sorted(source_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        destination = archive_dir / path.name
        shutil.copyfile(path, destination)
        copied.append(destination)
    return copied
