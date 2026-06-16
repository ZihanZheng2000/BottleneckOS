"""Evidence-backed Markdown thesis generation."""

from __future__ import annotations

from datetime import date

from .repository import Repository
from .scoring import bottleneck_score, evidence_rows, technology_detail, timeline_for_score


def generate_thesis(repo: Repository, technology_name: str, as_of: date) -> str:
    detail = technology_detail(repo, technology_name, as_of)
    technology = detail["technology"]
    score = bottleneck_score(repo, repo.technology_by_name(technology).id)
    evidence = evidence_rows(repo, repo.technology_by_name(technology).id)
    supporting = [item for item in evidence if item["claim_type"] != "counterargument"]
    counters = [item for item in evidence if item["claim_type"] == "counterargument"]

    if score is None:
        summary = (
            f"{technology} is being tracked, but the MVP does not yet have enough independent "
            "evidence to assign a precise bottleneck score."
        )
    else:
        summary = (
            f"{technology} currently scores {score}/100 as an AI infrastructure bottleneck. "
            f"The strongest mechanism is: {detail['evidence'][0]['claim'] if detail['evidence'] else 'insufficient evidence'}"
        )

    evidence_lines = "\n".join(
        f"{index}. {item['claim']} ({item['source_name']}, {item['published_at']})"
        for index, item in enumerate(supporting[:5], start=1)
    ) or "No supporting evidence available."
    counter_lines = "\n".join(
        f"- {item['claim']} ({item['source_name']})" for item in counters
    ) or "- No counterargument captured yet."

    affected = {
        "Power": "data center campuses, GPU cluster deployment, grid interconnects, substations",
        "Cooling": "dense racks, retrofit data centers, CDUs, liquid cooling supply chains",
        "CPO": "switch ASIC roadmaps, optical modules, silicon photonics, scale-out networking",
        "HBM": "accelerators, advanced packaging, DRAM suppliers, memory qualification",
        "Networking": "AI cluster fabrics, Ethernet switching, optical transceivers",
    }.get(technology, "AI infrastructure supply chain")

    return f"""# Bottleneck Thesis: {technology}

## Summary
{summary}

## Why This Matters
The constraint matters because it can slow the physical deployment of AI infrastructure even when accelerator demand remains strong.

## Key Evidence
{evidence_lines}

## Bottleneck Mechanics
The score combines demand growth, capacity tightness, lead time, technical difficulty, substitution difficulty, infrastructure dependency, and evidence quality. Current timeline estimate: {timeline_for_score(score)}.

## Affected Technologies
{affected}

## Counterarguments
{counter_lines}

## What Would Change Our Mind
Faster capacity additions, credible substitutions, shorter lead times, or multiple independent sources showing the constraint has eased would reduce this thesis.

## Confidence
{detail['status']} with average claim confidence {round(sum(item['confidence'] for item in evidence) / max(len(evidence), 1), 2)}.
"""
