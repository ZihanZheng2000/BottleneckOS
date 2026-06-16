"""Run-to-run comparison utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .coverage import coverage_summary
from .storage import load_repository_for_run


def load_score_rows(conn: sqlite3.Connection, run_id: str) -> dict[str, dict]:
    rows = conn.execute(
        """
        SELECT
            t.name AS technology,
            t.category AS category,
            s.attention_score,
            s.bottleneck_score,
            s.confidence,
            s.evidence_count,
            s.momentum,
            s.status,
            s.timeline,
            s.top_driver
        FROM score_snapshots s
        JOIN technologies t ON t.id = s.technology_id
        WHERE s.run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {row["technology"]: dict(row) for row in rows}


def load_run_metadata(conn: sqlite3.Connection, run_id: str) -> dict:
    row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise KeyError(f"Unknown run_id: {run_id}")
    return dict(row)


def compare_runs(conn: sqlite3.Connection, base_run_id: str, current_run_id: str) -> dict:
    base_scores = load_score_rows(conn, base_run_id)
    current_scores = load_score_rows(conn, current_run_id)
    technologies = sorted(set(base_scores) | set(current_scores))
    score_deltas = []
    for technology in technologies:
        before = base_scores.get(technology)
        after = current_scores.get(technology)
        before_score = before.get("bottleneck_score") if before else None
        after_score = after.get("bottleneck_score") if after else None
        before_attention = before.get("attention_score") if before else None
        after_attention = after.get("attention_score") if after else None
        score_deltas.append(
            {
                "technology": technology,
                "category": (after or before)["category"],
                "previous_score": before_score,
                "current_score": after_score,
                "score_delta": _delta(before_score, after_score),
                "previous_attention": before_attention,
                "current_attention": after_attention,
                "attention_delta": _delta(before_attention, after_attention),
                "previous_evidence": before.get("evidence_count") if before else 0,
                "current_evidence": after.get("evidence_count") if after else 0,
                "evidence_delta": (after.get("evidence_count") if after else 0)
                - (before.get("evidence_count") if before else 0),
                "status": _status(before, after),
            }
        )

    base_repo = load_repository_for_run(conn, base_run_id)
    current_repo = load_repository_for_run(conn, current_run_id)
    return {
        "base": load_run_metadata(conn, base_run_id),
        "current": load_run_metadata(conn, current_run_id),
        "score_deltas": sorted(
            score_deltas,
            key=lambda item: (
                item["score_delta"] is None,
                abs(item["score_delta"] or 0),
                item["technology"],
            ),
            reverse=True,
        ),
        "coverage": {
            "base": coverage_summary(base_repo),
            "current": coverage_summary(current_repo),
        },
    }


def render_diff_markdown(diff: dict) -> str:
    base = diff["base"]
    current = diff["current"]
    score_rows = [
        [
            row["technology"],
            row["previous_score"] if row["previous_score"] is not None else "NA",
            row["current_score"] if row["current_score"] is not None else "NA",
            _format_delta(row["score_delta"]),
            row["previous_evidence"],
            row["current_evidence"],
            _format_delta(row["evidence_delta"]),
            row["status"],
        ]
        for row in diff["score_deltas"]
    ]
    base_cov = diff["coverage"]["base"]
    current_cov = diff["coverage"]["current"]
    coverage_rows = [
        [
            "Core sources present",
            f"{base_cov['core_sources_present']}/{base_cov['core_sources_total']}",
            f"{current_cov['core_sources_present']}/{current_cov['core_sources_total']}",
            current_cov["core_sources_present"] - base_cov["core_sources_present"],
        ],
        [
            "Core technologies covered",
            f"{base_cov['core_technologies_covered']}/{base_cov['core_technologies_total']}",
            f"{current_cov['core_technologies_covered']}/{current_cov['core_technologies_total']}",
            current_cov["core_technologies_covered"] - base_cov["core_technologies_covered"],
        ],
    ]
    return f"""# Bottleneck OS Run Diff

## Runs

- Base: `{base['run_id']}` ({base['source']}, as of {base['as_of']})
- Current: `{current['run_id']}` ({current['source']}, as of {current['as_of']})

## Score Changes

{_table(['Technology', 'Prev Score', 'Current Score', 'Score Delta', 'Prev Evidence', 'Current Evidence', 'Evidence Delta', 'Status'], score_rows)}

## Coverage Changes

{_table(['Metric', 'Base', 'Current', 'Delta'], coverage_rows)}

## Remaining Current Coverage Gaps

- Missing core sources: {', '.join(current_cov['core_sources_missing']) or 'none'}
- Missing core technologies: {', '.join(current_cov['core_technologies_missing']) or 'none'}
"""


def write_diff_report(conn: sqlite3.Connection, base_run_id: str, current_run_id: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_diff_markdown(compare_runs(conn, base_run_id, current_run_id)), encoding="utf-8")
    return output_path


def _delta(before: int | float | None, after: int | float | None) -> int | float | None:
    if before is None or after is None:
        return None
    return after - before


def _status(before: dict | None, after: dict | None) -> str:
    if before is None:
        return "new"
    if after is None:
        return "removed"
    return "changed" if before != after else "unchanged"


def _format_delta(value: int | float | None) -> str:
    if value is None:
        return "NA"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value}"


def _table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])
