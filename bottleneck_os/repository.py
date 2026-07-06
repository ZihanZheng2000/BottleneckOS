"""In-memory repository for the MVP seed implementation."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from dataclasses import replace

from .models import Claim, Document, Technology
from .seed_data import CLAIMS, DOCUMENTS, TECHNOLOGIES

_version_counter = itertools.count()


@dataclass
class Repository:
    technologies: list[Technology]
    documents: list[Document]
    claims: list[Claim]

    def __post_init__(self) -> None:
        # Each Repository is treated as an immutable snapshot: callers build a
        # new instance instead of mutating one in place (see BottleneckHandler
        # `_ingest`). A monotonic version lets scoring cache derived results
        # per-instance without the id()-reuse hazard of caching on id(self).
        self._version = next(_version_counter)
        self._tech_by_id: dict[str, Technology] = {t.id: t for t in self.technologies}
        self._doc_by_id: dict[str, Document] = {d.id: d for d in self.documents}
        self._claims_by_tech: dict[str, list[Claim]] = {}
        for claim in self.claims:
            self._claims_by_tech.setdefault(claim.technology_id, []).append(claim)

    def technology_by_id(self, technology_id: str) -> Technology:
        try:
            return self._tech_by_id[technology_id]
        except KeyError:
            raise KeyError(f"Unknown technology id: {technology_id}")

    def technology_by_name(self, name: str) -> Technology:
        normalized = name.strip().lower()
        for technology in self.technologies:
            if technology.name.lower() == normalized or normalized in technology.aliases:
                return technology
        raise KeyError(f"Unknown technology: {name}")

    def document_by_id(self, doc_id: str) -> Document:
        try:
            return self._doc_by_id[doc_id]
        except KeyError:
            raise KeyError(f"Unknown document id: {doc_id}")

    def has_document(self, doc_id: str) -> bool:
        return doc_id in self._doc_by_id

    def claims_for_technology(self, technology_id: str) -> list[Claim]:
        return self._claims_by_tech.get(technology_id, [])


def build_seed_repository() -> Repository:
    return Repository(list(TECHNOLOGIES), _documents_with_evidence_excerpts(), list(CLAIMS))


def _documents_with_evidence_excerpts() -> list[Document]:
    quotes_by_doc: dict[str, list[str]] = {}
    for claim in CLAIMS:
        quotes_by_doc.setdefault(claim.doc_id, [])
        if claim.evidence_quote not in quotes_by_doc[claim.doc_id]:
            quotes_by_doc[claim.doc_id].append(claim.evidence_quote)

    documents: list[Document] = []
    for document in DOCUMENTS:
        quotes = quotes_by_doc.get(document.id, [])
        if not quotes:
            documents.append(document)
            continue
        excerpt_block = "\n\nEvidence excerpts:\n" + "\n".join(f"- {quote}" for quote in quotes)
        documents.append(replace(document, clean_text=document.clean_text.rstrip() + excerpt_block))
    return documents
