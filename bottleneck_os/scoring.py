"""Explainable scoring functions for Bottleneck OS."""

from __future__ import annotations

from collections import Counter
from datetime import date
from math import exp

from .models import Claim, Document, ScoreSnapshot, Technology
from .policy import EVIDENCE_GATE
from .repository import Repository

_gate_groups = EVIDENCE_GATE["required_claim_groups"]
DEMAND_TYPES: frozenset[str] = frozenset(_gate_groups["demand"])
CONSTRAINT_TYPES: frozenset[str] = frozenset(_gate_groups["constraint"])
COUNTER_TYPES: frozenset[str] = frozenset(_gate_groups["counterargument"])


def _recency_weight(published_at: date, as_of: date) -> float:
    age_days = max((as_of - published_at).days, 0)
    return 0.45 + 0.55 * exp(-age_days / 90)


def _normalize(value: float, maximum: float) -> int:
    if maximum <= 0:
        return 0
    return round(max(0, min(100, value / maximum * 100)))


def evidence_rows(repo: Repository, technology_id: str) -> list[dict]:
    rows = []
    for claim in repo.claims_for_technology(technology_id):
        doc = repo.document_by_id(claim.doc_id)
        rows.append(
            {
                "claim_id": claim.id,
                "claim_type": claim.claim_type,
                "claim": claim.claim,
                "quote": claim.evidence_quote,
                "confidence": claim.confidence,
                "impact": claim.impact,
                "source_name": doc.source_name,
                "source_type": doc.source_type,
                "published_at": doc.published_at.isoformat(),
                "url": doc.url,
            }
        )
    return rows


def evidence_is_sufficient(repo: Repository, technology_id: str) -> bool:
    claims = repo.claims_for_technology(technology_id)
    docs = [repo.document_by_id(claim.doc_id) for claim in claims]
    source_names = {doc.source_name for doc in docs}
    claim_types = {claim.claim_type for claim in claims}
    return (
        len(claims) >= EVIDENCE_GATE["min_evidence_items"]
        and len(source_names) >= EVIDENCE_GATE["min_independent_sources"]
        and bool(claim_types & DEMAND_TYPES)
        and bool(claim_types & CONSTRAINT_TYPES)
        and bool(claim_types & COUNTER_TYPES)
    )


def attention_scores(repo: Repository, as_of: date) -> dict[str, int]:
    raw_scores: dict[str, float] = {}
    for technology in repo.technologies:
        score = 0.0
        source_names = set()
        source_types = set()
        for claim in repo.claims_for_technology(technology.id):
            doc = repo.document_by_id(claim.doc_id)
            source_names.add(doc.source_name)
            source_types.add(doc.source_type)
            score += 10 * doc.reliability_weight * claim.confidence * _recency_weight(doc.published_at, as_of)
        score += 4 * len(source_names)
        score += 3 * len(source_types)
        score += 2 * len(repo.claims_for_technology(technology.id))
        raw_scores[technology.id] = score
    maximum = max(raw_scores.values(), default=1)
    return {technology_id: _normalize(score, maximum) for technology_id, score in raw_scores.items()}


def _average_impact(claims: list[Claim], claim_types: set[str], default: int) -> int:
    selected = [claim.impact for claim in claims if claim.claim_type in claim_types]
    if not selected:
        return default
    return round(sum(selected) / len(selected))


def bottleneck_breakdown(repo: Repository, technology_id: str) -> dict[str, int]:
    claims = repo.claims_for_technology(technology_id)
    demand = _average_impact(claims, DEMAND_TYPES, 45)
    capacity = _average_impact(claims, {"capacity_signal", "infrastructure_constraint"}, 50)
    technical = _average_impact(claims, {"technical_constraint", "infrastructure_constraint"}, 50)
    substitution = 100 - _average_impact(claims, {"substitution_signal", "counterargument"}, 42)
    infrastructure = _average_impact(claims, {"infrastructure_constraint"}, 48)
    lead_time = round((capacity + infrastructure) / 2)
    evidence_quality = min(
        100,
        round(
            18 * len(claims)
            + 8 * len({repo.document_by_id(claim.doc_id).source_name for claim in claims})
            + 4 * len({claim.claim_type for claim in claims})
        ),
    )
    return {
        "demand_growth": demand,
        "capacity_tightness": capacity,
        "lead_time": lead_time,
        "technical_difficulty": technical,
        "substitution_difficulty": substitution,
        "infrastructure_dependency": infrastructure,
        "evidence_quality": evidence_quality,
    }


def bottleneck_score(repo: Repository, technology_id: str) -> int | None:
    if not evidence_is_sufficient(repo, technology_id):
        return None
    parts = bottleneck_breakdown(repo, technology_id)
    score = (
        0.25 * parts["demand_growth"]
        + 0.20 * parts["capacity_tightness"]
        + 0.15 * parts["lead_time"]
        + 0.15 * parts["technical_difficulty"]
        + 0.10 * parts["substitution_difficulty"]
        + 0.10 * parts["infrastructure_dependency"]
        + 0.05 * parts["evidence_quality"]
    )
    return round(score)


def _momentum(score: int, claim_counts: Counter[str]) -> tuple[float, float, str]:
    recent = claim_counts["recent"]
    prior = claim_counts["prior"]
    growth_30d = (recent - prior) / max(prior, 1)
    growth_90d = score / 100
    if growth_30d > 0.4 and score >= 70:
        label = "explosive"
    elif growth_30d > 0.15:
        label = "rising"
    elif growth_30d < -0.15:
        label = "declining"
    else:
        label = "stable"
    return growth_30d, growth_90d, label


def score_snapshots(repo: Repository, as_of: date) -> list[ScoreSnapshot]:
    attention = attention_scores(repo, as_of)
    snapshots = []
    for technology in repo.technologies:
        claims = repo.claims_for_technology(technology.id)
        buckets: Counter[str] = Counter()
        for claim in claims:
            doc = repo.document_by_id(claim.doc_id)
            age = (as_of - doc.published_at).days
            buckets["recent" if age <= 45 else "prior"] += 1
        growth_30d, growth_90d, momentum = _momentum(attention[technology.id], buckets)
        score = bottleneck_score(repo, technology.id)
        confidence = round(sum(claim.confidence for claim in claims) / max(len(claims), 1), 2)
        driver = top_driver(repo, technology.id)
        snapshots.append(
            ScoreSnapshot(
                technology.id,
                as_of,
                attention[technology.id],
                growth_30d,
                growth_90d,
                momentum,
                score,
                confidence,
                len(claims),
                driver,
                timeline_for_score(score),
                "scored" if score is not None else "insufficient_evidence",
            )
        )
    return sorted(snapshots, key=lambda item: item.bottleneck_score or -1, reverse=True)


def top_driver(repo: Repository, technology_id: str) -> str:
    claims = sorted(repo.claims_for_technology(technology_id), key=lambda item: item.impact, reverse=True)
    return claims[0].claim if claims else "No claims available"


def timeline_for_score(score: int | None) -> str:
    if score is None:
        return "Unknown"
    if score >= 85:
        return "6-24 months"
    if score >= 70:
        return "12-36 months"
    return "24+ months"


def technology_radar(repo: Repository, as_of: date) -> list[dict]:
    snapshots = score_snapshots(repo, as_of)
    rows = []
    for snapshot in sorted(snapshots, key=lambda item: item.attention_score, reverse=True):
        tech = repo.technology_by_id(snapshot.technology_id)
        growth_label, momentum_label, interpretation = _technology_radar_interpretation(snapshot)
        rows.append(
            {
                "technology": tech.name,
                "category": tech.category,
                "attention_score": snapshot.attention_score,
                "growth_30d": snapshot.attention_growth_30d,
                "growth_30d_label": growth_label,
                "momentum": momentum_label,
                "evidence_count": snapshot.evidence_count,
                "interpretation": interpretation,
            }
        )
    return rows


def _technology_radar_interpretation(snapshot: ScoreSnapshot) -> tuple[str, str, str]:
    if snapshot.evidence_count == 0:
        return (
            "n/a",
            "low evidence",
            "No accepted evidence yet. This means the current source set is thin, not that the technology is irrelevant.",
        )
    if snapshot.evidence_count < 3:
        return (
            "n/a",
            "low evidence",
            "Limited evidence in the current source set. Treat attention as a coverage signal, not a bottleneck conclusion.",
        )
    if snapshot.evidence_count < 5:
        return (
            "insufficient history",
            "insufficient history",
            "Enough evidence to track attention, but not enough run history to interpret short-term momentum.",
        )
    return (
        f"{round(snapshot.attention_growth_30d * 100)}%",
        snapshot.momentum,
        "Momentum is based on evidence publication dates and should be confirmed with repeated ingestion runs.",
    )


def bottleneck_radar(repo: Repository, as_of: date) -> dict[str, list[dict]]:
    snapshots = score_snapshots(repo, as_of)
    scored = [snapshot for snapshot in snapshots if snapshot.bottleneck_score is not None]
    insufficient = [snapshot for snapshot in snapshots if snapshot.bottleneck_score is None]

    def row(snapshot: ScoreSnapshot) -> dict:
        tech = repo.technology_by_id(snapshot.technology_id)
        return {
            "technology": tech.name,
            "category": tech.category,
            "bottleneck_score": snapshot.bottleneck_score,
            "confidence": snapshot.confidence,
            "timeline": snapshot.timeline,
            "top_driver": snapshot.top_driver,
            "status": snapshot.status,
            "evidence_count": snapshot.evidence_count,
        }

    emerging = sorted(scored, key=lambda item: (item.attention_growth_30d, item.bottleneck_score or 0), reverse=True)
    declining = sorted(scored, key=lambda item: item.attention_growth_30d)
    return {
        "current": [row(item) for item in scored[:10]],
        "emerging": [row(item) for item in emerging[:10]],
        "declining": [row(item) for item in declining[:10]],
        "insufficient_evidence": [row(item) for item in insufficient],
    }


def technology_detail(repo: Repository, technology_name: str, as_of: date) -> dict:
    tech = repo.technology_by_name(technology_name)
    score = bottleneck_score(repo, tech.id)
    return {
        "technology": tech.name,
        "category": tech.category,
        "score": score,
        "status": "scored" if score is not None else "insufficient_evidence",
        "breakdown": bottleneck_breakdown(repo, tech.id),
        "evidence": evidence_rows(repo, tech.id),
        "counterarguments": [
            item for item in evidence_rows(repo, tech.id) if item["claim_type"] == "counterargument"
        ],
        "timeline": timeline_for_score(score),
        "as_of": as_of.isoformat(),
    }
