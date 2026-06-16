# Bottleneck OS Production Roadmap

The MVP proves the research loop. The production version must prove coverage, repeatability, traceability, and trust.

## Current State

Implemented:

- real public evidence records with URLs
- manual-trigger source extraction from Markdown files
- explainable scoring
- evidence gate
- dated reports
- source coverage audit
- technology policy coverage audit
- tests for API, scoring, reporting, extraction, and coverage
- SQLite run snapshot persistence
- run-to-run diff reports from persisted snapshots
- historical trend reports from persisted score snapshots
- production readiness audit for tests, reports, review artifacts, archive, database, and coverage gaps

Known gaps:

- no automatic URL/PDF fetcher yet
- no LLM extraction schema yet
- historical snapshots exist; trend reports now mark insufficient history when a 30-day or 90-day baseline is missing
- no source de-duplication across repeated runs
- no human review workflow for extracted claims
- limited UI surface for coverage gaps

## Production Pillars

### 1. Source Universe

Formal source policy is defined in:

- [SOURCE_POLICY.md](SOURCE_POLICY.md)
- [bottleneck_os/policy.py](bottleneck_os/policy.py)

Production requirement:

- every report must include source coverage
- missing core sources must be visible
- inaccessible or premium sources must be marked partial or missing

### 2. Technology Universe

Production requirement:

- core technologies must be tracked even when evidence is missing
- missing core technologies must appear in the coverage audit
- watch-list technologies should be added to scoring only after enough evidence exists

### 3. Ingestion

Near-term target:

- manual-trigger URL/PDF/text ingestion
- no daily automation required
- deterministic document IDs
- local archive of extracted text
- source metadata retained

Future target:

- scheduled refresh
- RSS/API support where available
- transcript and PDF processors
- per-source freshness policy

### 4. Extraction

Current extractor is rule-based and dependency-free.

Production target:

- strict JSON extraction schema
- claim type classification
- quote extraction
- technology normalization
- counterargument extraction
- confidence scoring
- human review state: pending, accepted, rejected

### 5. Storage

MVP uses in-memory seed data.

Production target:

- Postgres for documents, claims, entities, source runs, and reports
- pgvector or equivalent for semantic retrieval
- immutable report snapshots
- reproducible run IDs

### 6. Scoring

Current scoring is explainable and deterministic.

Production target:

- score versioning
- factor-level evidence links
- historical snapshots for real momentum
- minimum coverage requirements by category
- separate confidence from severity

### 7. Reporting

Current reports are dated Markdown files.

Production target:

- run report
- source coverage report
- technology coverage report
- thesis report per bottleneck
- change report between runs

### 8. Analyst UI

Current UI shows radar and thesis.

Production target:

- coverage dashboard
- evidence review queue
- technology detail pages
- source detail pages
- report history
- claim-level traceability

## Suggested Build Sequence

1. Replace seed data with generated data artifacts.
2. Add URL/PDF fetch command.
3. Add text archive and JSON claim output.
4. Add human-review flags for claims.
5. Add SQLite or Postgres persistence.
6. Add historical run snapshots.
7. Add coverage dashboard to UI.
8. Add LLM-backed extraction behind a strict schema.
9. Add regression tests for a fixed source fixture set.
10. Add source freshness and missing-source alerts.

## Production Acceptance Criteria

A production-quality run is acceptable only if:

- all source and technology coverage tables are present
- every scored bottleneck links to evidence quotes and URLs
- every score states confidence and missing evidence
- all core missing sources are explicitly listed
- tests pass
- the report is dated
- the scoring model version is recorded
- the run can be reproduced from stored source artifacts
