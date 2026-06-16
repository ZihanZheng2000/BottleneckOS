"""Coverage audits against the formal Bottleneck OS policy."""

from __future__ import annotations

from collections import defaultdict

from .policy import SOURCE_UNIVERSE, TECHNOLOGY_UNIVERSE, core_source_names, core_technology_names
from .repository import Repository
from .scoring import evidence_is_sufficient


def _matches_target(text_values: list[str], target_name: str, aliases: tuple[str, ...] = ()) -> bool:
    lowered_values = [value.lower() for value in text_values]
    tokens = (target_name.lower(), *(alias.lower() for alias in aliases))
    return any(token in value for token in tokens for value in lowered_values)


def source_coverage(repo: Repository) -> list[dict]:
    rows = []
    for target in sorted(SOURCE_UNIVERSE, key=lambda item: (item.priority, item.category, item.name)):
        matched = [
            document
            for document in repo.documents
            if _matches_target([document.source_name, document.title, document.clean_text], target.name)
        ]
        rows.append(
            {
                "source": target.name,
                "category": target.category,
                "priority": target.priority,
                "status": "present" if matched else "missing",
                "matched_documents": len(matched),
            }
        )
    return rows


def technology_policy_coverage(repo: Repository) -> list[dict]:
    evidence_by_technology = defaultdict(int)
    for claim in repo.claims:
        try:
            technology = repo.technology_by_id(claim.technology_id)
        except KeyError:
            continue
        evidence_by_technology[technology.name] += 1

    repo_technologies = {technology.name: technology for technology in repo.technologies}
    rows = []
    for target in TECHNOLOGY_UNIVERSE:
        direct = repo_technologies.get(target.name)
        matched_evidence = evidence_by_technology.get(target.name, 0)
        if not direct:
            for technology in repo.technologies:
                if _matches_target([technology.name, *technology.aliases], target.name, target.aliases):
                    direct = technology
                    matched_evidence = evidence_by_technology.get(technology.name, 0)
                    break
        if direct and evidence_is_sufficient(repo, direct.id):
            status = "covered"
        elif direct and matched_evidence:
            status = "partial"
        else:
            status = "missing"
        rows.append(
            {
                "technology": target.name,
                "category": target.category,
                "priority": target.priority,
                "status": status,
                "evidence_count": matched_evidence,
            }
        )
    return rows


def coverage_summary(repo: Repository) -> dict:
    sources = source_coverage(repo)
    technologies = technology_policy_coverage(repo)
    core_sources = core_source_names()
    core_technologies = core_technology_names()
    present_core_sources = {
        row["source"] for row in sources if row["priority"] == "core" and row["status"] == "present"
    }
    covered_core_technologies = {
        row["technology"] for row in technologies if row["priority"] == "core" and row["status"] == "covered"
    }
    partial_core_technologies = {
        row["technology"] for row in technologies if row["priority"] == "core" and row["status"] == "partial"
    }
    return {
        "core_sources_present": len(present_core_sources),
        "core_sources_total": len(core_sources),
        "core_sources_missing": sorted(core_sources - present_core_sources),
        "core_technologies_covered": len(covered_core_technologies),
        "core_technologies_total": len(core_technologies),
        "core_technologies_partial": sorted(partial_core_technologies),
        "core_technologies_missing": sorted(core_technologies - covered_core_technologies),
    }
