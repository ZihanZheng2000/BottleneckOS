"""Source acquisition planning for policy coverage gaps."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .coverage import technology_policy_coverage
from .policy import EVIDENCE_GATE, SOURCE_UNIVERSE, TECHNOLOGY_UNIVERSE, SourceTarget, TechnologyTarget
from .repository import Repository


TECHNOLOGY_SOURCE_MAP = {
    "GPU": ("NVIDIA", "Dylan Patel", "SemiAnalysis", "GTC"),
    "CoWoS": ("TSMC", "NVIDIA", "Dylan Patel", "SemiAnalysis"),
    "Switch ASIC": ("Dylan Patel", "SemiAnalysis", "Broadcom", "NVIDIA", "Arista", "OCP"),
    "Optical Transceiver": ("Dylan Patel", "SemiAnalysis", "Coherent", "Lumentum", "Broadcom", "OFC"),
    "Transformer": ("Dylan Patel", "SemiAnalysis", "IEA", "EIA", "Schneider Electric", "Uptime Institute"),
    "Rack Density": ("Dylan Patel", "SemiAnalysis", "NVIDIA", "OCP", "Uptime Institute", "Schneider Electric"),
}


CLAIM_GROUP_LABELS = {
    "demand": "demand-side growth signal",
    "constraint": "capacity, technical, infrastructure, or substitution constraint",
    "counterargument": "counterargument or uncertainty note",
}


def build_acquisition_plan(repo: Repository) -> list[dict]:
    coverage_rows = {
        row["technology"]: row for row in technology_policy_coverage(repo) if row["priority"] == "core"
    }
    targets_by_name = {target.name: target for target in TECHNOLOGY_UNIVERSE}
    sources_by_name = {source.name: source for source in SOURCE_UNIVERSE}

    plan = []
    for technology_name, row in coverage_rows.items():
        if row["status"] == "covered":
            continue
        technology = targets_by_name[technology_name]
        source_names = TECHNOLOGY_SOURCE_MAP.get(technology_name, _fallback_sources(technology))
        candidate_sources = [
            _source_candidate(sources_by_name[name], technology)
            for name in source_names
            if name in sources_by_name
        ]
        plan.append(
            {
                "technology": technology.name,
                "category": technology.category,
                "priority": technology.priority,
                "current_evidence_count": row["evidence_count"],
                "aliases": list(technology.aliases),
                "minimum_new_evidence_items": max(
                    0,
                    EVIDENCE_GATE["min_evidence_items"] - int(row["evidence_count"]),
                ),
                "candidate_sources": candidate_sources,
                "required_claim_groups": [
                    CLAIM_GROUP_LABELS[group] for group in EVIDENCE_GATE["required_claim_groups"]
                ],
                "search_queries": _search_queries(technology, candidate_sources),
            }
        )
    return plan


def render_acquisition_plan(plan: list[dict], as_of: date) -> str:
    if plan:
        summary = (
            f"{len(plan)} core technology gaps require source acquisition before the system can claim "
            "full core-universe coverage."
        )
    else:
        summary = "All core technologies have at least one accepted evidence item."

    sections = []
    for item in plan:
        source_rows = [
            [
                source["name"],
                source["category"],
                source["priority"],
                ", ".join(source["expected_source_types"]),
                source["rationale"],
            ]
            for source in item["candidate_sources"]
        ]
        sections.append(
            f"""## {item['technology']}

Category: {item['category']}

Current accepted evidence: {item['current_evidence_count']}

Minimum new evidence items before scoring: {item['minimum_new_evidence_items']}

Aliases / search terms: {', '.join(item['aliases'])}

Required evidence mix:

{_bullets(item['required_claim_groups'])}

Candidate source targets:

{_table(['Source', 'Category', 'Priority', 'Expected Types', 'Why It Matters'], source_rows)}

Search queries:

{_bullets(item['search_queries'])}
"""
        )

    return f"""# Bottleneck OS Source Acquisition Plan

Generated as of: {as_of.isoformat()}

## Summary

{summary}

This report is a collection plan, not evidence. It does not create claims, scores, or URLs by itself. New material must still move through archive, extraction, human review, and the evidence gate before it affects bottleneck results.

## Evidence Gate Reminder

- At least {EVIDENCE_GATE['min_evidence_items']} evidence items.
- At least {EVIDENCE_GATE['min_independent_sources']} independent source names.
- At least one demand-side signal.
- At least one constraint signal.
- At least one counterargument or uncertainty note.

{chr(10).join(sections) if sections else 'No open core technology acquisition gaps.'}
"""


def write_acquisition_plan(repo: Repository, as_of: date, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_acquisition_plan(build_acquisition_plan(repo), as_of), encoding="utf-8")
    return output_path


def _fallback_sources(technology: TechnologyTarget) -> tuple[str, ...]:
    category_matches = [
        source.name
        for source in SOURCE_UNIVERSE
        if source.category in {"expert_research", "conference"}
    ]
    if technology.category in {"Power", "Data Center", "Cooling"}:
        category_matches.extend(
            source.name
            for source in SOURCE_UNIVERSE
            if source.category in {"infrastructure_research", "infrastructure_vendor"}
        )
    return tuple(dict.fromkeys(category_matches[:4]))


def _source_candidate(source: SourceTarget, technology: TechnologyTarget) -> dict:
    return {
        "name": source.name,
        "category": source.category,
        "priority": source.priority,
        "expected_source_types": list(source.expected_source_types),
        "rationale": _rationale(source, technology),
    }


def _rationale(source: SourceTarget, technology: TechnologyTarget) -> str:
    if source.category == "expert_research":
        return f"independent analyst context for {technology.name} demand, supply, and counterarguments"
    if source.category == "primary_company":
        return f"primary product, capacity, roadmap, or earnings evidence for {technology.name}"
    if source.category == "infrastructure_research":
        return f"public infrastructure data relevant to {technology.name} constraints"
    if source.category == "infrastructure_vendor":
        return f"vendor field evidence on deployment constraints around {technology.name}"
    if source.category == "conference":
        return f"public technical talks and presentations mentioning {technology.name}"
    return f"supporting public evidence for {technology.name}"


def _search_queries(technology: TechnologyTarget, sources: list[dict]) -> list[str]:
    terms = [technology.name, *technology.aliases[:2]]
    queries = []
    for source in sources:
        for term in terms[:2]:
            queries.append(f'{source["name"]} "{term}" AI infrastructure bottleneck')
    return queries[:8]


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])
