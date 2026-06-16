"""Production readiness validation for Bottleneck OS artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .coverage import coverage_summary
from .evidence_audit import audit_evidence_traceability
from .repository import build_seed_repository
from .review import load_review_repository
from .schemas import validate_claim_records, validate_document_records
from .storage import connect, list_runs


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str


def run_readiness_audit(
    root: Path,
    as_of: str,
    db_path: Path | None = None,
    review_dir: Path | None = None,
    archive_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> dict:
    db_path = db_path or root / "data" / "bottleneck_os.sqlite"
    review_dir = review_dir or root / "review" / "current"
    archive_dir = archive_dir or root / "archive" / "sources"
    reports_dir = reports_dir or root / "reports"
    checks = [
        check_test_results(reports_dir / f"{as_of}_test-results.txt"),
        check_required_reports(reports_dir, as_of),
        check_review_artifacts(review_dir),
        check_evidence_traceability(review_dir),
        check_archive_artifacts(archive_dir),
        check_database_runs(db_path),
        check_policy_coverage(),
    ]
    errors = [check for check in checks if check.status == "error"]
    warnings = [check for check in checks if check.status == "warning"]
    return {
        "status": "ready_with_warnings" if not errors else "not_ready",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def check_test_results(path: Path) -> CheckResult:
    if not path.exists():
        return CheckResult("tests", "error", f"Missing test results: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if "OK" not in text or "FAILED" in text or "ERROR:" in text:
        return CheckResult("tests", "error", "Test results do not show a clean OK run")
    return CheckResult("tests", "pass", "Unit test results show OK")


def check_required_reports(reports_dir: Path, as_of: str) -> CheckResult:
    required = [
        f"{as_of}_report.md",
        f"{as_of}_test-results.txt",
        f"{as_of}_historical_trends.md",
        f"{as_of}_run_diff.md",
        f"{as_of}_acquisition_plan.md",
    ]
    missing = [name for name in required if not (reports_dir / name).exists()]
    if missing:
        return CheckResult("reports", "error", f"Missing dated reports: {', '.join(missing)}")
    return CheckResult("reports", "pass", "Required dated reports are present")


def check_review_artifacts(review_dir: Path) -> CheckResult:
    documents_path = review_dir / "documents.jsonl"
    claims_path = review_dir / "claims.jsonl"
    if not documents_path.exists() or not claims_path.exists():
        return CheckResult("review", "warning", "Review artifacts are missing; extraction review queue is empty")
    documents = _read_jsonl(documents_path)
    claims = _read_jsonl(claims_path)
    schema_errors = validate_document_records(documents)
    schema_errors.extend(validate_claim_records(claims, {record.get("id") for record in documents}))
    if schema_errors:
        return CheckResult("review", "error", "Schema errors: " + "; ".join(schema_errors[:5]))
    if not claims:
        return CheckResult("review", "warning", "Review claims file exists but contains no claims")
    return CheckResult("review", "pass", f"Review artifacts contain {len(claims)} claim records")


def check_evidence_traceability(review_dir: Path) -> CheckResult:
    documents_path = review_dir / "documents.jsonl"
    claims_path = review_dir / "claims.jsonl"
    if not documents_path.exists() or not claims_path.exists():
        return CheckResult("evidence", "warning", "Review artifacts are missing; evidence traceability was not checked")
    try:
        repo = load_review_repository(review_dir, include_statuses={"accepted"})
    except Exception as exc:
        return CheckResult("evidence", "error", f"Could not load accepted review claims: {exc}")
    audit = audit_evidence_traceability(repo)
    if audit["errors"]:
        return CheckResult("evidence", "error", "Traceability errors: " + "; ".join(audit["errors"][:5]))
    if not audit["claims_checked"]:
        return CheckResult("evidence", "warning", "No accepted claims were available for traceability audit")
    return CheckResult(
        "evidence",
        "pass",
        f"Verified {audit['claims_checked']} accepted claims against {audit['documents_checked']} source documents",
    )


def check_archive_artifacts(archive_dir: Path) -> CheckResult:
    if not archive_dir.exists():
        return CheckResult("archive", "warning", "Archive directory is missing")
    markdown = [path for path in archive_dir.glob("*.md")]
    if not markdown:
        return CheckResult("archive", "warning", "Archive contains no source markdown files")
    missing_raw = [path.name for path in markdown if not (path.with_suffix(".raw")).exists()]
    if missing_raw:
        return CheckResult("archive", "warning", f"Some archived markdown files have no raw pair: {', '.join(missing_raw[:5])}")
    return CheckResult("archive", "pass", f"Archive contains {len(markdown)} source markdown files with raw pairs")


def check_database_runs(db_path: Path) -> CheckResult:
    if not db_path.exists():
        return CheckResult("database", "error", f"Missing SQLite database: {db_path}")
    conn = connect(db_path)
    try:
        runs = list_runs(conn)
    finally:
        conn.close()
    if not runs:
        return CheckResult("database", "error", "SQLite database contains no run snapshots")
    return CheckResult("database", "pass", f"SQLite contains {len(runs)} run snapshots")


def check_policy_coverage() -> CheckResult:
    summary = coverage_summary(build_seed_repository())
    if summary["core_technologies_missing"]:
        return CheckResult(
            "coverage",
            "warning",
            "Core technology gaps remain: " + ", ".join(summary["core_technologies_missing"]),
        )
    return CheckResult("coverage", "pass", "All core technologies are covered")


def render_readiness_markdown(audit: dict, as_of: str) -> str:
    rows = [
        [check.name, check.status, check.message]
        for check in audit["checks"]
    ]
    return f"""# Bottleneck OS Production Readiness Audit

Generated as of: {as_of}

Overall status: **{audit['status']}**

{_table(['Check', 'Status', 'Message'], rows)}

## Interpretation

- `pass`: requirement is satisfied.
- `warning`: production can continue, but the limitation must stay visible.
- `error`: production readiness is blocked until fixed.
"""


def write_readiness_report(audit: dict, as_of: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_readiness_markdown(audit, as_of), encoding="utf-8")
    return output_path


def _read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def _table(headers: list[str], rows: list[list[object]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])
