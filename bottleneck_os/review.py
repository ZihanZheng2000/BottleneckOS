"""Claim review artifacts for production-style extraction workflows."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import Claim, Document, Technology
from .repository import Repository
from .seed_data import TECHNOLOGIES

VALID_REVIEW_STATUSES = {"pending", "accepted", "rejected"}


def document_to_record(document: Document) -> dict:
    data = asdict(document)
    data["published_at"] = document.published_at.isoformat()
    return data


def claim_to_review_record(claim: Claim, status: str = "pending", reviewer_note: str = "") -> dict:
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}")
    data = asdict(claim)
    data["review_status"] = status
    data["reviewer_note"] = reviewer_note
    return data


def technology_to_record(technology: Technology) -> dict:
    return asdict(technology)


def _technology_from_record(record: dict) -> Technology:
    return Technology(
        record["id"],
        record["name"],
        record["category"],
        tuple(record.get("aliases", ())),
        record.get("status", "confirmed"),
    )


def write_review_artifacts(
    repo: Repository,
    output_dir: Path,
    default_status: str = "pending",
    overwrite: bool = True,
) -> tuple[Path, Path]:
    if default_status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {default_status}")
    output_dir.mkdir(parents=True, exist_ok=True)
    documents_path = output_dir / "documents.jsonl"
    claims_path = output_dir / "claims.jsonl"
    technologies_path = output_dir / "technologies.jsonl"
    mode = "w" if overwrite else "x"
    with documents_path.open(mode, encoding="utf-8") as handle:
        for document in repo.documents:
            handle.write(json.dumps(document_to_record(document), sort_keys=True) + "\n")
    with claims_path.open(mode, encoding="utf-8") as handle:
        for claim in repo.claims:
            handle.write(json.dumps(claim_to_review_record(claim, default_status), sort_keys=True) + "\n")
    with technologies_path.open(mode, encoding="utf-8") as handle:
        for technology in repo.technologies:
            handle.write(json.dumps(technology_to_record(technology), sort_keys=True) + "\n")
    return documents_path, claims_path


def load_review_repository(
    artifact_dir: Path,
    technologies: list[Technology] | None = None,
    include_statuses: set[str] | None = None,
) -> Repository:
    base_technologies = list(technologies or TECHNOLOGIES)
    include_statuses = include_statuses or {"accepted"}
    unknown_statuses = include_statuses - VALID_REVIEW_STATUSES
    if unknown_statuses:
        raise ValueError(f"Invalid review statuses: {', '.join(sorted(unknown_statuses))}")

    technologies_path = artifact_dir / "technologies.jsonl"
    discovered = (
        [_technology_from_record(record) for record in _read_jsonl(technologies_path)]
        if technologies_path.exists()
        else []
    )
    known_ids = {technology.id for technology in base_technologies}
    merged_technologies = base_technologies + [tech for tech in discovered if tech.id not in known_ids]

    documents = [_document_from_record(record) for record in _read_jsonl(artifact_dir / "documents.jsonl")]
    claims: list[Claim] = []
    for record in _read_jsonl(artifact_dir / "claims.jsonl"):
        status = record.get("review_status", "pending")
        if status in include_statuses:
            claims.append(_claim_from_record(record))
    return Repository(merged_technologies, documents, claims)


def set_all_claim_statuses(artifact_dir: Path, status: str) -> Path:
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}")
    claims_path = artifact_dir / "claims.jsonl"
    records = _read_jsonl(claims_path)
    with claims_path.open("w", encoding="utf-8") as handle:
        for record in records:
            record["review_status"] = status
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return claims_path


def update_claim_review(
    artifact_dir: Path,
    claim_id: str,
    review_status: str,
    reviewer_note: str | None = None,
) -> dict:
    if review_status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {review_status}")
    claims_path = artifact_dir / "claims.jsonl"
    records = _read_jsonl(claims_path)
    updated: dict | None = None
    for record in records:
        if record.get("id") == claim_id:
            record["review_status"] = review_status
            if reviewer_note is not None:
                record["reviewer_note"] = reviewer_note
            updated = record
            break
    if updated is None:
        raise KeyError(claim_id)
    with claims_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return updated


def review_summary(artifact_dir: Path) -> dict[str, int]:
    counts = {status: 0 for status in VALID_REVIEW_STATUSES}
    claims_path = artifact_dir / "claims.jsonl"
    if not claims_path.exists():
        return counts
    for record in _read_jsonl(claims_path):
        status = record.get("review_status", "pending")
        if status in counts:
            counts[status] += 1
    return counts


def review_claim_records(artifact_dir: Path, limit: int | None = None) -> list[dict]:
    claims_path = artifact_dir / "claims.jsonl"
    if not claims_path.exists():
        return []
    records = _read_jsonl(claims_path)
    if limit is not None:
        return records[:limit]
    return records


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def _document_from_record(record: dict) -> Document:
    from datetime import date

    return Document(
        record["id"],
        record["title"],
        record["source_name"],
        record["source_type"],
        date.fromisoformat(record["published_at"]),
        record["url"],
        record["clean_text"],
        float(record["reliability_weight"]),
    )


def _claim_from_record(record: dict) -> Claim:
    return Claim(
        record["id"],
        record["doc_id"],
        record["technology_id"],
        record["claim_type"],
        record["claim"],
        record["evidence_quote"],
        float(record["confidence"]),
        int(record["impact"]),
    )
