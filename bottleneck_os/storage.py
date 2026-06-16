"""SQLite persistence for run snapshots."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from .models import Claim, Document, ScoreSnapshot, Technology
from .repository import Repository
from .scoring import score_snapshots

SCHEMA_VERSION = 1


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            as_of TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            report_path TEXT
        );

        CREATE TABLE IF NOT EXISTS technologies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            aliases TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            published_at TEXT NOT NULL,
            url TEXT NOT NULL,
            clean_text TEXT NOT NULL,
            reliability_weight REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL REFERENCES documents(id),
            technology_id TEXT NOT NULL REFERENCES technologies(id),
            claim_type TEXT NOT NULL,
            claim TEXT NOT NULL,
            evidence_quote TEXT NOT NULL,
            confidence REAL NOT NULL,
            impact INTEGER NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'accepted'
        );

        CREATE TABLE IF NOT EXISTS run_documents (
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            doc_id TEXT NOT NULL REFERENCES documents(id),
            PRIMARY KEY (run_id, doc_id)
        );

        CREATE TABLE IF NOT EXISTS run_claims (
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            claim_id TEXT NOT NULL REFERENCES claims(id),
            PRIMARY KEY (run_id, claim_id)
        );

        CREATE TABLE IF NOT EXISTS score_snapshots (
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            technology_id TEXT NOT NULL REFERENCES technologies(id),
            as_of TEXT NOT NULL,
            attention_score INTEGER NOT NULL,
            attention_growth_30d REAL NOT NULL,
            attention_growth_90d REAL NOT NULL,
            momentum TEXT NOT NULL,
            bottleneck_score INTEGER,
            confidence REAL NOT NULL,
            evidence_count INTEGER NOT NULL,
            top_driver TEXT NOT NULL,
            timeline TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (run_id, technology_id)
        );
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()


def create_run_id(as_of: date, source: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_source = "".join(ch if ch.isalnum() else "_" for ch in source).strip("_").lower()
    return f"{as_of.isoformat()}_{safe_source}_{timestamp}"


def persist_run(
    conn: sqlite3.Connection,
    repo: Repository,
    as_of: date,
    source: str,
    report_path: Path | None = None,
    run_id: str | None = None,
    review_status: str = "accepted",
) -> str:
    run_id = run_id or create_run_id(as_of, source)
    created_at = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            "INSERT INTO runs(run_id, as_of, created_at, source, report_path) VALUES (?, ?, ?, ?, ?)",
            (run_id, as_of.isoformat(), created_at, source, str(report_path) if report_path else None),
        )
        for technology in repo.technologies:
            conn.execute(
                """
                INSERT OR REPLACE INTO technologies(id, name, category, aliases)
                VALUES (?, ?, ?, ?)
                """,
                (technology.id, technology.name, technology.category, "|".join(technology.aliases)),
            )
        for document in repo.documents:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents(
                    id, title, source_name, source_type, published_at, url, clean_text, reliability_weight
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.title,
                    document.source_name,
                    document.source_type,
                    document.published_at.isoformat(),
                    document.url,
                    document.clean_text,
                    document.reliability_weight,
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO run_documents(run_id, doc_id) VALUES (?, ?)",
                (run_id, document.id),
            )
        for claim in repo.claims:
            conn.execute(
                """
                INSERT OR REPLACE INTO claims(
                    id, doc_id, technology_id, claim_type, claim, evidence_quote, confidence, impact, review_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.id,
                    claim.doc_id,
                    claim.technology_id,
                    claim.claim_type,
                    claim.claim,
                    claim.evidence_quote,
                    claim.confidence,
                    claim.impact,
                    review_status,
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO run_claims(run_id, claim_id) VALUES (?, ?)",
                (run_id, claim.id),
            )
        for snapshot in score_snapshots(repo, as_of):
            conn.execute(
                """
                INSERT OR REPLACE INTO score_snapshots(
                    run_id, technology_id, as_of, attention_score, attention_growth_30d,
                    attention_growth_90d, momentum, bottleneck_score, confidence,
                    evidence_count, top_driver, timeline, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    snapshot.technology_id,
                    snapshot.date.isoformat(),
                    snapshot.attention_score,
                    snapshot.attention_growth_30d,
                    snapshot.attention_growth_90d,
                    snapshot.momentum,
                    snapshot.bottleneck_score,
                    snapshot.confidence,
                    snapshot.evidence_count,
                    snapshot.top_driver,
                    snapshot.timeline,
                    snapshot.status,
                ),
            )
    return run_id


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            r.run_id,
            r.as_of,
            r.created_at,
            r.source,
            r.report_path,
            COUNT(DISTINCT rd.doc_id) AS document_count,
            COUNT(DISTINCT rc.claim_id) AS claim_count
        FROM runs r
        LEFT JOIN run_documents rd ON rd.run_id = r.run_id
        LEFT JOIN run_claims rc ON rc.run_id = r.run_id
        GROUP BY r.run_id
        ORDER BY r.created_at DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def load_repository_for_run(conn: sqlite3.Connection, run_id: str) -> Repository:
    from datetime import date as date_type

    technologies = [
        Technology(row["id"], row["name"], row["category"], tuple(filter(None, row["aliases"].split("|"))))
        for row in conn.execute("SELECT * FROM technologies ORDER BY id").fetchall()
    ]
    documents = [
        Document(
            row["id"],
            row["title"],
            row["source_name"],
            row["source_type"],
            date_type.fromisoformat(row["published_at"]),
            row["url"],
            row["clean_text"],
            row["reliability_weight"],
        )
        for row in conn.execute(
            """
            SELECT d.*
            FROM documents d
            JOIN run_documents rd ON rd.doc_id = d.id
            WHERE rd.run_id = ?
            ORDER BY d.id
            """,
            (run_id,),
        ).fetchall()
    ]
    claims = [
        Claim(
            row["id"],
            row["doc_id"],
            row["technology_id"],
            row["claim_type"],
            row["claim"],
            row["evidence_quote"],
            row["confidence"],
            row["impact"],
        )
        for row in conn.execute(
            """
            SELECT c.*
            FROM claims c
            JOIN run_claims rc ON rc.claim_id = c.id
            WHERE rc.run_id = ?
              AND c.review_status = 'accepted'
            ORDER BY c.id
            """,
            (run_id,),
        ).fetchall()
    ]
    return Repository(technologies, documents, claims)
