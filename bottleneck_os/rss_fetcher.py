"""RSS/Atom feed fetcher.

Parses RSS 2.0 and Atom 1.0 feeds, then archives each item as a source
markdown file compatible with the existing extractor and ingest pipeline.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from .fetcher import ManifestItem, fetch_url, render_source_markdown, source_text_for_item

_ATOM_NS = "http://www.w3.org/2005/Atom"

_DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
)

_DEFAULT_USER_AGENT = "BottleneckOS/0.1 research-bot"

# EDGAR index pages contain this string; the actual filing doc is one link deeper
_EDGAR_INDEX_MARKER = "EDGAR Filing Documents"


def _edgar_user_agent() -> str:
    contact = os.getenv("BOTTLENECK_OS_CONTACT_EMAIL", "").strip()
    if contact:
        return f"BottleneckOS research-bot (contact: {contact})"
    return "BottleneckOS research-bot"


def _edgar_resolve_doc_url(index_url: str, html_text: str) -> str | None:
    """Return the best document URL from an EDGAR filing index page.

    Priority:
    1. Exhibit 99.x or earnings press release (highest-signal content)
    2. Main filing via iXBRL viewer
    3. Any direct .htm filing link (older filings)
    """
    # Collect all .htm links — both direct and inside iXBRL viewer wrappers
    all_htm: list[str] = re.findall(
        r'href="(?:/ix\?doc=)?(/Archives/edgar/data/[^"]+\.htm)"',
        html_text, re.IGNORECASE,
    )

    # Priority 1: Exhibit 99 (standard name) or press-release-style filenames
    _PR_PATTERNS = re.compile(
        r"(?:ex99|ex-99|exhibit99|pressrelease|press.?release|[_-]pr\.htm|earnings|cfocommentary)",
        re.IGNORECASE,
    )
    for href in all_htm:
        if _PR_PATTERNS.search(href) and "_htm.xml" not in href:
            return "https://www.sec.gov" + href

    # Priority 2: iXBRL viewer (main 8-K/6-K document)
    ixbrl = re.findall(
        r'href="/ix\?doc=(/Archives/edgar/data/[^"]+\.htm)"',
        html_text, re.IGNORECASE,
    )
    if ixbrl:
        return "https://www.sec.gov" + ixbrl[0]

    # Priority 3: Any direct .htm link that isn't boilerplate
    for href in all_htm:
        if "-index" not in href and "_htm.xml" not in href:
            return "https://www.sec.gov" + href

    return None


@dataclass
class FeedConfig:
    source_name: str
    source_type: str
    rss_url: str
    reliability_weight: float = 0.85
    max_items: int = 10
    fetch_full_article: bool = True


def parse_feed_config(path: Path) -> list[FeedConfig]:
    configs: list[FeedConfig] = []
    current: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "---":
            if current:
                configs.append(_make_config(current))
                current = {}
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current[key.strip().lower()] = value.strip()
    if current:
        configs.append(_make_config(current))
    return configs


def _make_config(data: dict[str, str]) -> FeedConfig:
    for required in ("source_name", "rss_url"):
        if required not in data:
            raise ValueError(f"Feed config missing required key: {required}")
    return FeedConfig(
        source_name=data["source_name"],
        source_type=data.get("source_type", "news"),
        rss_url=data["rss_url"],
        reliability_weight=float(data.get("reliability_weight", "0.85")),
        max_items=int(data.get("max_items", "10")),
        fetch_full_article=data.get("fetch_full_article", "true").lower() != "false",
    )


def _parse_date(text: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


def _el_text(parent: ET.Element, tag: str, ns: str = "", default: str = "") -> str:
    qualified = f"{{{ns}}}{tag}" if ns else tag
    el = parent.find(qualified)
    return (el.text or default).strip() if el is not None else default


def _atom_link(entry: ET.Element) -> str:
    for el in entry.findall(f"{{{_ATOM_NS}}}link"):
        rel = el.get("rel", "alternate")
        if rel in ("alternate", ""):
            return el.get("href", "")
    el = entry.find(f"{{{_ATOM_NS}}}link")
    return el.get("href", "") if el is not None else ""


def parse_feed_items(xml_bytes: bytes) -> list[dict]:
    try:
        root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
    except ET.ParseError as exc:
        raise ValueError(f"Invalid RSS/Atom XML: {exc}") from exc

    # Atom 1.0
    if root.tag in (f"{{{_ATOM_NS}}}feed", "feed"):
        entries = root.findall(f"{{{_ATOM_NS}}}entry") or root.findall("entry")
        items = []
        for entry in entries:
            title = _el_text(entry, "title", _ATOM_NS) or _el_text(entry, "title")
            link = _atom_link(entry)
            summary = (
                _el_text(entry, "summary", _ATOM_NS)
                or _el_text(entry, "content", _ATOM_NS)
                or _el_text(entry, "summary")
            )
            published = (
                _el_text(entry, "published", _ATOM_NS)
                or _el_text(entry, "updated", _ATOM_NS)
            )
            items.append({"title": title, "link": link, "description": summary, "pub_date": published})
        return items

    # RSS 2.0
    channel = root.find("channel") or root
    items = []
    for item in channel.findall("item"):
        items.append({
            "title": _el_text(item, "title"),
            "link": _el_text(item, "link"),
            "description": _el_text(item, "description"),
            "pub_date": _el_text(item, "pubDate"),
        })
    return items


def _is_edgar_url(url: str) -> bool:
    return "sec.gov" in url or "edgar" in url.lower()


def fetch_feed_to_archive(
    config: FeedConfig,
    archive_dir: Path,
    *,
    timeout: int = 20,
) -> list[Path]:
    archive_dir.mkdir(parents=True, exist_ok=True)

    user_agent = _edgar_user_agent() if _is_edgar_url(config.rss_url) else _DEFAULT_USER_AGENT
    feed_bytes, _ = fetch_url(config.rss_url, timeout=timeout, user_agent=user_agent)
    items = parse_feed_items(feed_bytes)[: config.max_items]

    safe_source = re.sub(r"[^A-Za-z0-9]+", "_", config.source_name).strip("_").lower()
    archived: list[Path] = []

    for item in items:
        title = (item.get("title") or "Untitled").strip()
        link = (item.get("link") or "").strip()
        description = (item.get("description") or "").strip()
        pub_date_str = (item.get("pub_date") or "").strip()

        try:
            pub_date = _parse_date(pub_date_str) if pub_date_str else date.today()
        except Exception:
            pub_date = date.today()

        url_key = link or title
        url_hash = hashlib.sha1(url_key.encode("utf-8")).hexdigest()[:12]
        output_path = archive_dir / f"{pub_date.isoformat()}_{safe_source}_{url_hash}.md"

        if output_path.exists():
            archived.append(output_path)
            continue

        canonical_url = link or f"rss://{safe_source}/{url_hash}"
        manifest_item = ManifestItem(
            title=title,
            source_name=config.source_name,
            source_type=config.source_type,
            published_at=pub_date.isoformat(),
            url=canonical_url,
            reliability_weight=str(config.reliability_weight),
        )

        body = description
        status = "rss_summary"
        content_kind = "rss"

        if config.fetch_full_article and link and link.startswith("http"):
            item_agent = _edgar_user_agent() if _is_edgar_url(link) else _DEFAULT_USER_AGENT
            try:
                article_bytes, content_type = fetch_url(link, timeout=timeout, user_agent=item_agent)
                # EDGAR: check raw HTML for index marker before stripping tags,
                # then follow the link to the actual filing document
                if _is_edgar_url(link):
                    raw_html = article_bytes.decode("utf-8", errors="replace")
                    if _EDGAR_INDEX_MARKER in raw_html:
                        doc_url = _edgar_resolve_doc_url(link, raw_html)
                        if doc_url:
                            article_bytes, content_type = fetch_url(doc_url, timeout=timeout, user_agent=item_agent)
                            manifest_item = ManifestItem(
                                title=manifest_item.title,
                                source_name=manifest_item.source_name,
                                source_type=manifest_item.source_type,
                                published_at=manifest_item.published_at,
                                url=doc_url,
                                reliability_weight=manifest_item.reliability_weight,
                            )
                content_kind, fetched_body = source_text_for_item(manifest_item, article_bytes, content_type)
                if fetched_body.strip():
                    body = fetched_body
                    status = "fetched"
            except Exception:
                pass  # keep RSS summary

        output_path.write_text(
            render_source_markdown(manifest_item, status, content_kind, body or title),
            encoding="utf-8",
        )
        archived.append(output_path)

    return archived
