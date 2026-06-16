"""Markdown report generation for Bottleneck OS runs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .coverage import coverage_summary, source_coverage, technology_policy_coverage
from .expert_signal import expert_signal_by_technology, expert_signal_summary, expert_source_coverage
from .repository import Repository
from .scoring import bottleneck_radar, evidence_is_sufficient, evidence_rows, technology_detail, technology_radar
from .thesis import generate_thesis


def evidence_gap_analysis(repo: Repository) -> list[dict]:
    rows = []
    for technology in repo.technologies:
        rows_for_tech = evidence_rows(repo, technology.id)
        claim_types = {row["claim_type"] for row in rows_for_tech}
        source_names = {row["source_name"] for row in rows_for_tech}
        missing = []
        if len(rows_for_tech) < 3:
            missing.append("needs at least 3 evidence items")
        if len(source_names) < 2:
            missing.append("needs at least 2 independent source names")
        if "demand_signal" not in claim_types:
            missing.append("needs demand-side signal")
        if not claim_types.intersection(
            {"capacity_signal", "technical_constraint", "infrastructure_constraint", "substitution_signal"}
        ):
            missing.append("needs capacity, technical, infrastructure, or substitution constraint signal")
        if "counterargument" not in claim_types:
            missing.append("needs counterargument or uncertainty note")
        rows.append(
            {
                "technology": technology.name,
                "sufficient": evidence_is_sufficient(repo, technology.id),
                "evidence_count": len(rows_for_tech),
                "source_count": len(source_names),
                "claim_types": sorted(claim_types),
                "missing": missing,
            }
        )
    return rows


def _table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def document_source_table(repo: Repository) -> str:
    return _table(
        ["Source", "Type", "Date", "Title", "URL"],
        [
            [
                document.source_name,
                document.source_type,
                document.published_at.isoformat(),
                document.title,
                document.url,
            ]
            for document in sorted(repo.documents, key=lambda item: (item.source_name, item.published_at))
        ],
    )


def generate_run_report(repo: Repository, as_of: date, test_results: str | None = None) -> str:
    bottlenecks = bottleneck_radar(repo, as_of)
    technologies = technology_radar(repo, as_of)
    gaps = evidence_gap_analysis(repo)
    sources = source_coverage(repo)
    tech_policy = technology_policy_coverage(repo)
    summary_stats = coverage_summary(repo)
    expert_summary = expert_signal_summary(repo)
    expert_sources = expert_source_coverage(repo)
    expert_technologies = expert_signal_by_technology(repo)
    scored_names = [row["technology"] for row in bottlenecks["current"]]
    insufficient_names = [row["technology"] for row in bottlenecks["insufficient_evidence"]]
    if insufficient_names:
        summary = (
            f"The current MVP assigns bottleneck scores to {', '.join(scored_names)}. "
            f"{', '.join(insufficient_names)} are tracked but remain below the evidence gate."
        )
        improvement_intro = "For each insufficient technology, add evidence until it passes all gates:"
    else:
        summary = (
            f"The current MVP assigns bottleneck scores to all tracked technologies: {', '.join(scored_names)}. "
            "Power ranks first, followed by Cooling, Networking, CPO, and HBM."
        )
        improvement_intro = (
            "All tracked technologies pass the current evidence gate. Further improvement should focus on source depth, "
            "automation, and stronger counterevidence rather than merely clearing the minimum threshold:"
        )

    bottleneck_table = _table(
        ["Rank", "Technology", "Score", "Confidence", "Timeline", "Top Driver"],
        [
            [
                index,
                row["technology"],
                row["bottleneck_score"],
                f"{round(row['confidence'] * 100)}%",
                row["timeline"],
                row["top_driver"],
            ]
            for index, row in enumerate(bottlenecks["current"], start=1)
        ],
    )
    insufficient_table = _table(
        ["Technology", "Category", "Evidence", "Status", "Next Step"],
        [
            [
                row["technology"],
                row["category"],
                row.get("evidence_count", 0),
                row["status"],
                "Add evidence through acquisition and review workflow",
            ]
            for row in bottlenecks["insufficient_evidence"]
        ],
    )

    attention_table = _table(
        ["Technology", "Attention", "30d Growth", "Momentum", "Evidence"],
        [
            [
                row["technology"],
                row["attention_score"],
                f"{round(row['growth_30d'] * 100)}%",
                row["momentum"],
                row["evidence_count"],
            ]
            for row in technologies
        ],
    )

    gap_table = _table(
        ["Technology", "Sufficient", "Evidence", "Sources", "Missing"],
        [
            [
                row["technology"],
                "yes" if row["sufficient"] else "no",
                row["evidence_count"],
                row["source_count"],
                "; ".join(row["missing"]) or "none",
            ]
            for row in gaps
        ],
    )

    source_table = _table(
        ["Source Target", "Category", "Priority", "Status", "Matched Documents"],
        [[row["source"], row["category"], row["priority"], row["status"], row["matched_documents"]] for row in sources],
    )
    expert_source_table = _table(
        ["Expert Source", "Priority", "Status", "Matched Documents"],
        [[row["source"], row["priority"], row["status"], row["matched_documents"]] for row in expert_sources],
    )
    expert_technology_table = _table(
        ["Technology", "Category", "Expert Status", "Expert Evidence", "Expert Sources"],
        [
            [
                row["technology"],
                row["category"],
                row["status"],
                row["expert_evidence_count"],
                ", ".join(row["expert_sources"]) or "none",
            ]
            for row in expert_technologies
        ],
    )

    technology_policy_table = _table(
        ["Technology Target", "Category", "Priority", "Status", "Evidence"],
        [
            [row["technology"], row["category"], row["priority"], row["status"], row["evidence_count"]]
            for row in tech_policy
        ],
    )

    details = []
    for row in bottlenecks["current"]:
        detail = technology_detail(repo, row["technology"], as_of)
        details.append(
            f"""### {row['technology']}

- Bottleneck score: {detail['score']}/100
- Timeline: {detail['timeline']}
- Evidence items: {len(detail['evidence'])}
- Counterarguments: {len(detail['counterarguments'])}
- Top evidence: {detail['evidence'][0]['claim'] if detail['evidence'] else 'none'}
"""
        )

    power_thesis = generate_thesis(repo, "Power", as_of)
    tests_section = test_results.strip() if test_results else "Test output not attached to this report."

    return f"""# Bottleneck OS Run Report

Generated as of: {as_of.isoformat()}

## Executive Summary

{summary}

## Bottleneck Results

{bottleneck_table}

## Technology Attention Radar

Note: attention growth is currently a recency proxy from curated evidence dates, not a true time-series trend. Automated ingestion with historical snapshots is required before treating this as a rigorous 30-day growth metric.

{attention_table}

## Evidence Gap Analysis

{gap_table}

## Source Coverage

Core sources present: {summary_stats['core_sources_present']}/{summary_stats['core_sources_total']}

{source_table}

## Expert Signal Coverage

Expert sources present: {expert_summary['expert_sources_present']}/{expert_summary['expert_sources_total']}

Missing expert sources: {', '.join(expert_summary['expert_sources_missing']) or 'none'}

Core technologies with expert signal: {expert_summary['technologies_with_expert_signal']}/{expert_summary['core_technologies_total']}

Core technologies missing expert signal: {', '.join(expert_summary['technologies_missing_expert_signal']) or 'none'}

{expert_source_table}

{expert_technology_table}

## Technology Policy Coverage

Core technologies covered: {summary_stats['core_technologies_covered']}/{summary_stats['core_technologies_total']}

Partial core technologies: {', '.join(summary_stats['core_technologies_partial']) or 'none'}

Core technologies below full evidence gate: {', '.join(summary_stats['core_technologies_missing']) or 'none'}

{technology_policy_table}

## Tracked Technologies Below Evidence Gate

{insufficient_table}

## Evidence Source URLs

{document_source_table(repo)}

Important note: this run uses curated real public source records with URLs. It is no longer based on synthetic seed snippets. The remaining limitation is that ingestion is still manual-curated rather than automated crawling, and some premium/paywalled sources such as full SemiAnalysis research may not be fully represented.

## Evidence Quality Improvements

{improvement_intro}

- At least 3 evidence items.
- At least 2 independent source names.
- At least 1 demand-side signal.
- At least 1 capacity, technical, infrastructure, or substitution constraint signal.
- At least 1 counterargument or uncertainty note.

Recommended next evidence targets:

- HBM: Micron, SK Hynix, Samsung, TSMC packaging commentary, NVIDIA memory roadmap references, SemiAnalysis memory supply analysis.
- Networking: NVIDIA, Broadcom, Arista, Ethernet/InfiniBand conference talks, hyperscaler fabric design commentary.
- CPO: Broadcom, NVIDIA, TSMC silicon photonics commentary, Lumentum, Coherent, optical module ecosystem notes, SemiAnalysis optical roadmap analysis.

## Scored Bottleneck Details

{chr(10).join(details)}

## Example Generated Thesis

{power_thesis}

## Test Results

```text
{tests_section}
```
"""


def write_run_report(repo: Repository, as_of: date, output_path: Path, test_results_path: Path | None = None) -> Path:
    test_results = None
    if test_results_path and test_results_path.exists():
        test_results = test_results_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_run_report(repo, as_of, test_results), encoding="utf-8")
    return output_path
