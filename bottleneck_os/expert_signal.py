"""Expert-source coverage checks for early bottleneck signals."""

from __future__ import annotations

from .policy import SOURCE_UNIVERSE, core_technology_names
from .repository import Repository


def expert_source_targets() -> list:
    return [source for source in SOURCE_UNIVERSE if source.category == "expert_research"]


def expert_source_coverage(repo: Repository) -> list[dict]:
    rows = []
    for source in expert_source_targets():
        matched = [
            document
            for document in repo.documents
            if _matches_source(document.source_name, document.title, document.clean_text, source.name)
        ]
        rows.append(
            {
                "source": source.name,
                "priority": source.priority,
                "status": "present" if matched else "missing",
                "matched_documents": len(matched),
            }
        )
    return rows


def expert_signal_by_technology(repo: Repository) -> list[dict]:
    core_names = core_technology_names()
    rows = []
    for technology in repo.technologies:
        if technology.name not in core_names:
            continue
        expert_sources = set()
        evidence_count = 0
        for claim in repo.claims_for_technology(technology.id):
            document = repo.document_by_id(claim.doc_id)
            matched_source = _matched_expert_source(document.source_name, document.title, document.clean_text)
            if matched_source:
                expert_sources.add(matched_source)
                evidence_count += 1
        rows.append(
            {
                "technology": technology.name,
                "category": technology.category,
                "status": "present" if evidence_count else "missing",
                "expert_evidence_count": evidence_count,
                "expert_sources": sorted(expert_sources),
            }
        )
    return rows


def expert_signal_summary(repo: Repository) -> dict:
    source_rows = expert_source_coverage(repo)
    technology_rows = expert_signal_by_technology(repo)
    missing_sources = [row["source"] for row in source_rows if row["status"] == "missing"]
    missing_technologies = [row["technology"] for row in technology_rows if row["status"] == "missing"]
    return {
        "expert_sources_present": sum(1 for row in source_rows if row["status"] == "present"),
        "expert_sources_total": len(source_rows),
        "expert_sources_missing": missing_sources,
        "technologies_with_expert_signal": sum(1 for row in technology_rows if row["status"] == "present"),
        "core_technologies_total": len(technology_rows),
        "technologies_missing_expert_signal": missing_technologies,
    }


def _matched_expert_source(source_name: str, title: str, clean_text: str) -> str | None:
    for source in expert_source_targets():
        if _matches_source(source_name, title, clean_text, source.name):
            return source.name
    return None


def _matches_source(source_name: str, title: str, clean_text: str, target_name: str) -> bool:
    target = target_name.lower()
    return any(target in value.lower() for value in (source_name, title, clean_text))
