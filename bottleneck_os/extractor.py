"""Manual-trigger evidence extraction from source text files.

This is intentionally dependency-free. It is not a replacement for a full LLM
extractor, but it turns pasted source material into auditable Document and Claim
objects without hand-writing claims in Python.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from .models import Claim, Document, Technology
from .seed_data import TECHNOLOGIES

CLAIM_KEYWORDS = {
    "demand_signal": (
        "demand",
        "growth",
        "surged",
        "accelerating",
        "expanding",
        "rising",
        "scale",
        "adoption",
        "need",
        "requires",
    ),
    "capacity_signal": (
        "capacity",
        "supply",
        "sold out",
        "ramp",
        "shortage",
        "constrained",
        "constraint",
        "qualification",
    ),
    "technical_constraint": (
        "technical",
        "architecture",
        "density",
        "power density",
        "thermal",
        "cooling",
        "bandwidth",
        "latency",
        "reliability",
    ),
    "infrastructure_constraint": (
        "grid",
        "interconnection",
        "substation",
        "transformer",
        "facility",
        "permits",
        "construction",
        "space",
        "water",
    ),
    "substitution_signal": (
        "ethernet",
        "ecosystem",
        "alternative",
        "substitute",
        "pluggable",
        "options",
        "open",
    ),
    "counterargument": (
        "however",
        "but",
        "mitigate",
        "reduce",
        "improve",
        "alternative",
        "can address",
        "can reduce",
        "progress",
    ),
}

IMPACT_BY_TYPE = {
    "demand_signal": 84,
    "capacity_signal": 80,
    "technical_constraint": 78,
    "infrastructure_constraint": 86,
    "substitution_signal": 58,
    "counterargument": 46,
}


def parse_source_file(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, str] = {}
    body_lines: list[str] = []
    in_header = True
    for line in text.splitlines():
        if in_header and line.strip() == "---":
            in_header = False
            continue
        if in_header and ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip()
        else:
            in_header = False
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    if not body:
        raise ValueError(f"Source file has no body text: {path}")
    return metadata, body


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [part.strip() for part in parts if len(part.strip()) >= 40]


def technology_matches(sentence: str, technologies: list[Technology]) -> list[Technology]:
    lowered = sentence.lower()
    matches = []
    for technology in technologies:
        tokens = (technology.name.lower(), *technology.aliases)
        if any(token.lower() in lowered for token in tokens):
            matches.append(technology)
    return matches


def classify_claim_type(sentence: str) -> str | None:
    lowered = sentence.lower()
    scores = {
        claim_type: sum(1 for keyword in keywords if keyword in lowered)
        for claim_type, keywords in CLAIM_KEYWORDS.items()
    }
    claim_type, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return None
    return claim_type


def infer_claim(sentence: str, technology: Technology, claim_type: str) -> str:
    cleaned = sentence.strip()
    if len(cleaned) <= 220:
        return cleaned
    return f"{cleaned[:217].rstrip()}..."


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def extract_document_and_claims(path: Path, technologies: list[Technology] | None = None) -> tuple[Document, list[Claim]]:
    technologies = technologies or list(TECHNOLOGIES)
    metadata, body = parse_source_file(path)
    published_at = date.fromisoformat(metadata.get("published_at", date.today().isoformat()))
    source_name = metadata.get("source_name", path.stem)
    source_type = metadata.get("source_type", "source_text")
    title = metadata.get("title", path.stem.replace("_", " ").title())
    url = metadata.get("url", f"file://{path.resolve()}")
    reliability_weight = float(metadata.get("reliability_weight", "0.8"))
    doc_id = _stable_id("doc", source_name, title, url)
    document = Document(doc_id, title, source_name, source_type, published_at, url, body, reliability_weight)

    claims: list[Claim] = []
    seen = set()
    for sentence in split_sentences(body):
        claim_type = classify_claim_type(sentence)
        if claim_type is None:
            continue
        for technology in technology_matches(sentence, technologies):
            key = (technology.id, claim_type, sentence)
            if key in seen:
                continue
            seen.add(key)
            claim_id = _stable_id("claim", doc_id, technology.id, claim_type, sentence)
            confidence = 0.72 if source_type in {"blog", "product_page"} else 0.78
            claims.append(
                Claim(
                    claim_id,
                    doc_id,
                    technology.id,
                    claim_type,
                    infer_claim(sentence, technology, claim_type),
                    sentence,
                    confidence,
                    IMPACT_BY_TYPE[claim_type],
                )
            )
    return document, claims


def extract_repository_from_directory(source_dir: Path, technologies: list[Technology] | None = None):
    from .repository import Repository

    technologies = list(technologies or TECHNOLOGIES)
    documents: list[Document] = []
    claims: list[Claim] = []
    for path in sorted(source_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        document, extracted = extract_document_and_claims(path, technologies)
        documents.append(document)
        claims.extend(extracted)
    return Repository(technologies, documents, claims)
