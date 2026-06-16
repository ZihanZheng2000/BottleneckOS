# Contributing

Contributions should preserve Bottleneck OS's evidence-first contract.

## Development setup

```powershell
py -m pip install -e ".[dev]"
pytest -q
```

Install LLM providers only when needed:

```powershell
py -m pip install -e ".[llm]"
```

## Data rules

- Do not commit `.env`, API keys, SQLite databases, fetched archives, review queues, or generated reports.
- Do not add fabricated source records to `sources/`.
- Test fixtures may use controlled sample text, but application-facing manifests and docs should point to real public sources.
- Every production claim must keep a source URL and an evidence quote that can be traced back to stored source text.

## Before opening a pull request

Run:

```powershell
pytest -q
pytest tests/test_evidence_audit.py -q
```

If the change affects ingestion, review artifacts, reporting, or scoring, also run:

```powershell
py scripts/production_audit.py --as-of <YYYY-MM-DD>
```
