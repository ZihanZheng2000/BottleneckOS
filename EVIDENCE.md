# Evidence and Data Integrity

Bottleneck OS is designed to avoid fabricated evidence.

## What counts as evidence

Each evidence-backed claim must have:

- a source document with title, source name, source type, publication date, URL, and source text
- a claim type such as `demand_signal`, `capacity_signal`, `technical_constraint`, or `counterargument`
- an `evidence_quote` that appears in the stored source text
- a confidence score and impact score
- a review status when claims come from extraction artifacts

## Real public data

The built-in seed repository uses curated public-source records with URLs. The URL ingestion manifest in `sources/manifest.real.txt` points to real public pages from NVIDIA, TSMC, and Broadcom. RSS/API ingestion is configured in `sources/feeds.txt` for SEC EDGAR, EIA, DOE, and public company sources.

Generated artifacts are intentionally not committed:

- `archive/` stores fetched source snapshots
- `review/` stores extracted claim review queues
- `data/` stores SQLite run history
- `reports/` stores generated reports

These directories are ignored so the repository stays source-code-first while allowing every local run to produce auditable artifacts.

## Traceability audit

Run:

```powershell
pytest tests/test_evidence_audit.py -q
```

The audit verifies that every built-in claim has a public URL source and that every `evidence_quote` is present in the stored source text.

For production-style runs, use:

```powershell
py scripts/production_audit.py --as-of <YYYY-MM-DD>
```

The production audit checks tests, required reports, review artifact schemas, accepted-claim traceability, archived sources, database snapshots, and policy coverage.

## Human review expectation

LLM extraction is a drafting tool, not an authority. Claims extracted with `--llm` should be reviewed before being used in formal reports. Use `review_status: accepted` only after the source URL and evidence quote have been checked.
