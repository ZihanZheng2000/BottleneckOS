"""Strict schema validation for Bottleneck OS JSONL artifacts."""

from __future__ import annotations

from datetime import date

CLAIM_TYPES = {
    "demand_signal",
    "capacity_signal",
    "technical_constraint",
    "infrastructure_constraint",
    "substitution_signal",
    "counterargument",
}

REVIEW_STATUSES = {"pending", "accepted", "rejected"}

DOCUMENT_REQUIRED_FIELDS = {
    "id": str,
    "title": str,
    "source_name": str,
    "source_type": str,
    "published_at": str,
    "url": str,
    "clean_text": str,
    "reliability_weight": (int, float),
}

CLAIM_REQUIRED_FIELDS = {
    "id": str,
    "doc_id": str,
    "technology_id": str,
    "claim_type": str,
    "claim": str,
    "evidence_quote": str,
    "confidence": (int, float),
    "impact": int,
    "review_status": str,
    "reviewer_note": str,
}


def validate_document_record(record: dict, index: int | None = None) -> list[str]:
    prefix = _prefix("document", index)
    errors = _validate_required_fields(record, DOCUMENT_REQUIRED_FIELDS, prefix)
    if not errors:
        errors.extend(_validate_date(record["published_at"], f"{prefix}.published_at"))
        errors.extend(_validate_nonempty(record, ["id", "title", "source_name", "source_type", "url", "clean_text"], prefix))
        if not str(record["url"]).startswith(("http://", "https://", "file://", "seed://")):
            errors.append(f"{prefix}.url must start with http://, https://, file://, or seed://")
        weight = float(record["reliability_weight"])
        if weight < 0 or weight > 1:
            errors.append(f"{prefix}.reliability_weight must be between 0 and 1")
    return errors


def validate_claim_record(record: dict, index: int | None = None) -> list[str]:
    prefix = _prefix("claim", index)
    errors = _validate_required_fields(record, CLAIM_REQUIRED_FIELDS, prefix)
    if not errors:
        errors.extend(
            _validate_nonempty(
                record,
                ["id", "doc_id", "technology_id", "claim_type", "claim", "evidence_quote", "review_status"],
                prefix,
            )
        )
        if record["claim_type"] not in CLAIM_TYPES:
            errors.append(f"{prefix}.claim_type invalid: {record['claim_type']}")
        if record["review_status"] not in REVIEW_STATUSES:
            errors.append(f"{prefix}.review_status invalid: {record['review_status']}")
        confidence = float(record["confidence"])
        if confidence < 0 or confidence > 1:
            errors.append(f"{prefix}.confidence must be between 0 and 1")
        impact = int(record["impact"])
        if impact < 0 or impact > 100:
            errors.append(f"{prefix}.impact must be between 0 and 100")
    return errors


def validate_document_records(records: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_ids = set()
    for index, record in enumerate(records, start=1):
        errors.extend(validate_document_record(record, index))
        record_id = record.get("id")
        if record_id in seen_ids:
            errors.append(f"document[{index}].id duplicate: {record_id}")
        seen_ids.add(record_id)
    return errors


def validate_claim_records(records: list[dict], document_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    seen_ids = set()
    for index, record in enumerate(records, start=1):
        errors.extend(validate_claim_record(record, index))
        record_id = record.get("id")
        if record_id in seen_ids:
            errors.append(f"claim[{index}].id duplicate: {record_id}")
        seen_ids.add(record_id)
        if document_ids is not None and record.get("doc_id") not in document_ids:
            errors.append(f"claim[{index}].doc_id has no matching document: {record.get('doc_id')}")
    return errors


def _validate_required_fields(record: dict, schema: dict, prefix: str) -> list[str]:
    errors = []
    for field, expected_type in schema.items():
        if field not in record:
            errors.append(f"{prefix}.{field} is missing")
        elif not isinstance(record[field], expected_type):
            errors.append(f"{prefix}.{field} has invalid type")
    return errors


def _validate_nonempty(record: dict, fields: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{field} must be non-empty" for field in fields if not str(record.get(field, "")).strip()]


def _validate_date(value: str, field_name: str) -> list[str]:
    try:
        date.fromisoformat(value)
    except ValueError:
        return [f"{field_name} must be ISO date YYYY-MM-DD"]
    return []


def _prefix(kind: str, index: int | None) -> str:
    return f"{kind}[{index}]" if index is not None else kind
