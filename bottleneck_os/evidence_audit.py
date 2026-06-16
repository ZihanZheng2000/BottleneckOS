"""Evidence traceability checks for documents and extracted claims."""

from __future__ import annotations

import re

from .repository import Repository


def audit_evidence_traceability(repo: Repository, require_public_urls: bool = True) -> dict:
    """Check that every claim can be traced back to source text.

    The audit is intentionally deterministic and local: it does not re-fetch
    URLs. It verifies that the repository already contains enough evidence to
    explain each claim without relying on memory, model output, or trust.
    """
    errors: list[str] = []
    warnings: list[str] = []

    documents = {document.id: document for document in repo.documents}
    for document in repo.documents:
        if require_public_urls and not document.url.startswith(("http://", "https://")):
            errors.append(f"document {document.id} does not use a public URL: {document.url}")
        if not document.clean_text.strip():
            errors.append(f"document {document.id} has no source text")

    for claim in repo.claims:
        document = documents.get(claim.doc_id)
        if document is None:
            errors.append(f"claim {claim.id} references missing document {claim.doc_id}")
            continue
        if not claim.evidence_quote.strip():
            errors.append(f"claim {claim.id} has no evidence quote")
            continue
        if not _quote_is_in_text(claim.evidence_quote, document.clean_text):
            errors.append(f"claim {claim.id} quote is not present in document {document.id}")
        if claim.confidence < 0.5:
            warnings.append(f"claim {claim.id} has low confidence: {claim.confidence:.2f}")

    return {
        "status": "pass" if not errors else "fail",
        "documents_checked": len(repo.documents),
        "claims_checked": len(repo.claims),
        "errors": errors,
        "warnings": warnings,
    }


def _quote_is_in_text(quote: str, text: str) -> bool:
    normalized_quote = _normalize(quote)
    normalized_text = _normalize(text)
    if normalized_quote in normalized_text:
        return True
    # Some extractors trim long source sentences. Keep the audit strict, but
    # allow a substantial quoted prefix to avoid false failures on ellipsized text.
    quote_words = normalized_quote.split()
    if len(quote_words) >= 12:
        prefix = " ".join(quote_words[:12])
        return prefix in normalized_text
    return False


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()
