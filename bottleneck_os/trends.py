"""Historical trend calculations over persisted run snapshots."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path


def historical_trends(conn: sqlite3.Connection, as_of: date, windows: tuple[int, ...] = (30, 90)) -> list[dict]:
    latest_rows = _latest_rows_by_technology(conn, as_of)
    rows = []
    for technology_id, latest in latest_rows.items():
        item = {
            "technology_id": technology_id,
            "technology": latest["technology"],
            "category": latest["category"],
            "as_of": latest["as_of"],
            "current_bottleneck_score": latest["bottleneck_score"],
            "current_attention_score": latest["attention_score"],
            "current_evidence_count": latest["evidence_count"],
        }
        for window in windows:
            baseline = _baseline_row(conn, technology_id, as_of - timedelta(days=window), as_of)
            prefix = f"{window}d"
            if baseline is None:
                item[f"{prefix}_status"] = "insufficient_history"
                item[f"{prefix}_score_delta"] = None
                item[f"{prefix}_attention_delta"] = None
                item[f"{prefix}_evidence_delta"] = None
            else:
                item[f"{prefix}_status"] = "calculated"
                item[f"{prefix}_baseline_as_of"] = baseline["as_of"]
                item[f"{prefix}_score_delta"] = _delta(baseline["bottleneck_score"], latest["bottleneck_score"])
                item[f"{prefix}_attention_delta"] = _delta(baseline["attention_score"], latest["attention_score"])
                item[f"{prefix}_evidence_delta"] = latest["evidence_count"] - baseline["evidence_count"]
        rows.append(item)
    return sorted(
        rows,
        key=lambda row: (
            row["current_bottleneck_score"] is None,
            -(row["current_bottleneck_score"] or -1),
            row["technology"],
        ),
    )


def render_trends_markdown(trends: list[dict], as_of: date) -> str:
    rows = []
    for row in trends:
        rows.append(
            [
                row["technology"],
                row["current_bottleneck_score"] if row["current_bottleneck_score"] is not None else "NA",
                row["current_attention_score"],
                _format_delta(row.get("30d_score_delta")),
                _format_delta(row.get("30d_attention_delta")),
                _format_delta(row.get("30d_evidence_delta")),
                row.get("30d_status", "insufficient_history"),
                _format_delta(row.get("90d_score_delta")),
                row.get("90d_status", "insufficient_history"),
            ]
        )
    return f"""# Bottleneck OS Historical Trends

Generated as of: {as_of.isoformat()}

Historical trend values are calculated from persisted run snapshots. If no baseline run exists inside a window, the row is marked `insufficient_history`.

{_table(['Technology', 'Score', 'Attention', '30d Score', '30d Attention', '30d Evidence', '30d Status', '90d Score', '90d Status'], rows)}
"""


def write_trends_report(conn: sqlite3.Connection, as_of: date, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_trends_markdown(historical_trends(conn, as_of), as_of), encoding="utf-8")
    return output_path


def _latest_rows_by_technology(conn: sqlite3.Connection, as_of: date) -> dict[str, dict]:
    rows = conn.execute(
        """
        SELECT
            s.*,
            t.name AS technology,
            t.category AS category,
            r.created_at AS run_created_at
        FROM score_snapshots s
        JOIN technologies t ON t.id = s.technology_id
        JOIN runs r ON r.run_id = s.run_id
        WHERE s.as_of <= ?
        ORDER BY s.technology_id, s.as_of DESC, r.created_at DESC, s.run_id DESC
        """,
        (as_of.isoformat(),),
    ).fetchall()
    latest: dict[str, dict] = {}
    for row in rows:
        latest.setdefault(row["technology_id"], dict(row))
    return latest


def _baseline_row(conn: sqlite3.Connection, technology_id: str, window_start: date, as_of: date) -> dict | None:
    row = conn.execute(
        """
        SELECT *
        FROM score_snapshots s
        JOIN runs r ON r.run_id = s.run_id
        WHERE s.technology_id = ?
          AND s.as_of >= ?
          AND s.as_of < ?
        ORDER BY s.as_of ASC, r.created_at ASC, s.run_id ASC
        LIMIT 1
        """,
        (technology_id, window_start.isoformat(), as_of.isoformat()),
    ).fetchone()
    return dict(row) if row else None


def _delta(before: int | float | None, after: int | float | None) -> int | float | None:
    if before is None or after is None:
        return None
    return after - before


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
