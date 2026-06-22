"""Domain models for the Bottleneck OS MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Technology:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    status: str = "confirmed"  # "confirmed" (seeded ontology) or "provisional" (discovered from materials)


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    source_name: str
    source_type: str
    published_at: date
    url: str
    clean_text: str
    reliability_weight: float


@dataclass(frozen=True)
class Claim:
    id: str
    doc_id: str
    technology_id: str
    claim_type: str
    claim: str
    evidence_quote: str
    confidence: float
    impact: int


@dataclass(frozen=True)
class ScoreSnapshot:
    technology_id: str
    date: date
    attention_score: int
    attention_growth_30d: float
    attention_growth_90d: float
    momentum: str
    bottleneck_score: int | None
    confidence: float
    evidence_count: int
    top_driver: str
    timeline: str
    status: str = "scored"
