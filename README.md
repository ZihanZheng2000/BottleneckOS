# Bottleneck OS

[English](README.md) | [中文](README.zh-CN.md)

**Identify tomorrow's AI infrastructure bottlenecks before the market does.**

Bottleneck OS is an open-source AI infrastructure intelligence platform that detects emerging technology bottlenecks before they become market consensus.

Using LLM-powered evidence extraction from SEC filings, government reports, earnings transcripts, and industry news, it continuously evaluates constraints across GPUs, High Bandwidth Memory (HBM), datacenter power, networking, cooling, CoWoS advanced packaging, Co-Packaged Optics (CPO), and related technologies.

The project turns public evidence into a traceable bottleneck radar for AI infrastructure, GPU supply chain analysis, AI investment research, equity research, financial analysis, investment thesis work, alternative data, evidence extraction, market intelligence, and knowledge graph workflows.

| Feature | Status |
|---|---|
| Evidence ingestion | Yes |
| LLM claim extraction | Yes |
| Bottleneck radar | Yes |
| Web UI | Yes |
| Historical trends | Yes |
| JSON API | Yes |
| Evidence traceability audit | Yes |

See [EVIDENCE.md](EVIDENCE.md) for the data-integrity and traceability standard.

The research workflow was inspired by Serenity's evidence-first research method: start from public primary sources, preserve the evidence trail, and separate what is known from what still needs coverage.

---

## What it tracks

Bottleneck OS monitors eleven core technology categories:

| Technology | Category | What it constrains |
|---|---|---|
| HBM (High Bandwidth Memory) | Memory | GPU memory bandwidth; limits model size and throughput |
| Networking / InfiniBand | Interconnect | GPU cluster scaling; limits training run size |
| CPO (Co-Packaged Optics) | Interconnect | Next-gen datacenter bandwidth; long lead-time transition |
| Power Infrastructure | Power | Datacenter build-out; grid interconnection queues |
| Cooling Systems | Thermal | Rack density limits; liquid cooling retrofit timelines |
| GPU | Compute | Direct AI compute supply |
| CoWoS (Advanced Packaging) | Packaging | TSMC packaging capacity gating HBM+GPU |
| Switch ASIC | Networking | Spine/leaf switching for AI clusters |
| Optical Transceiver | Interconnect | 800G/1.6T transceiver supply vs. datacenter demand |
| Transformer (Electrical) | Power | Substation delivery; 2–4 year lead times |
| Rack Density | Infrastructure | Power-per-rack limits in existing facilities |

---

## How it works

```
Public Sources                  Evidence Pipeline               Output
─────────────                   ─────────────────               ──────
SEC EDGAR filings    ┐
EIA / DOE reports    ├─► fetch ─► LLM extraction ─► scoring ─► Bottleneck Radar
Analyst newsletters  ┘           (claim types)       (0-100)    API · Reports · UI
```

**Evidence types extracted per document:**

- `demand_signal` — demand growth evidence for a technology
- `capacity_signal` — supply shortfalls, sold-out capacity, ramp constraints
- `technical_constraint` — architecture, density, thermal, or bandwidth limits
- `infrastructure_constraint` — grid, permits, construction, lead-time constraints
- `substitution_signal` — alternatives that could reduce the bottleneck
- `counterargument` — evidence that challenges the bottleneck thesis

**Scoring gate:** a technology only receives a bottleneck score (0–100) once it has evidence from at least 3 independent sources covering demand, constraint, and counterargument claim types. Technologies below the gate are tracked but shown as `insufficient_evidence`.

**Bottleneck score** is a weighted composite of demand growth, capacity tightness, lead time, technical difficulty, substitution difficulty, and infrastructure dependency — each derived from the extracted claim set.

---

## Requirements

Python 3.10 or later.

For LLM-powered extraction, install at least one of:

```
pip install -e ".[dev]"
pip install -e ".[llm]"   # optional, for OpenAI/Anthropic extraction
```

Copy `.env.example` to `.env` and add your API key:

```
OPENAI_API_KEY=sk-proj-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

On Windows, use `py` instead of `python3`.

---

## Quickstart

**1. Start the API and UI (curated real public source records)**

```powershell
py -m bottleneck_os --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` — the built-in UI shows the bottleneck radar. The server starts with curated real public source records covering HBM, Power, Networking, CPO, and Cooling.

**2. Fetch fresh evidence and extract claims**

```powershell
# Fetch configured RSS feeds (SEC EDGAR companies, EIA, DOE)
py scripts/fetch_feeds.py --feeds sources/feeds.txt --archive-dir archive/sources

# Extract claims with LLM and auto-accept them
py scripts/extract_claims.py --source-dir archive/sources --llm --auto-accept
```

The `--llm` flag uses the API key in `.env`. Without it, a keyword-based fallback extractor runs instead (no API key required, lower accuracy).

For one-off URL ingestion from real public pages, use `sources/manifest.real.txt`:

```powershell
py scripts/fetch_sources.py --manifest sources/manifest.real.txt --archive-dir archive/sources
```

**3. Restart the server with extracted claims merged in**

```powershell
py -m bottleneck_os --host 127.0.0.1 --port 8000 --review-dir review/current
```

The server merges the curated public-source records with accepted extracted claims for a richer evidence base.

**4. Generate a report**

```powershell
$TODAY = Get-Date -Format "yyyy-MM-dd"
py scripts/generate_report.py --as-of $TODAY
```

Output: `reports/<TODAY>_report.md`

---

## Feed sources

Configured in `sources/feeds.txt`. Default feeds:

| Source | Ticker | Type | What it covers |
|---|---|---|---|
| SEC EDGAR — NVDA 8-K | NVDA | sec_filing | NVIDIA earnings, Blackwell/GPU supply, datacenter demand |
| SEC EDGAR — AMD 8-K | AMD | sec_filing | AMD GPU supply, AI accelerator demand, supply chain |
| SEC EDGAR — TSM 6-K | TSM | sec_filing | TSMC CoWoS packaging capacity, process node updates |
| SEC EDGAR — AVGO 8-K | AVGO | sec_filing | Broadcom Tomahawk/Jericho switch ASICs, AI networking |
| SEC EDGAR — VRT 8-K | VRT | sec_filing | Vertiv datacenter power, cooling, rack density |
| SEC EDGAR — COHR 8-K | COHR | sec_filing | Coherent 800G/1.6T optical transceivers |
| SEC EDGAR — LITE 8-K | LITE | sec_filing | Lumentum optical components for AI datacenters |
| SEC EDGAR — ETN 8-K | ETN | sec_filing | Eaton power distribution, electrical transformers, UPS |
| EIA Today in Energy | — | government_report | US electricity demand, grid capacity, datacenter power |
| DOE News | — | government_report | Grid modernization, energy infrastructure policy |

All EDGAR feeds automatically follow filing index pages to the earnings press release (Exhibit 99.1). Add more feeds by appending entries to `sources/feeds.txt`.

---

## Review workflow

For a curated run with human review before scoring:

```powershell
# Extract claims into a reviewable JSONL file
py scripts/extract_claims.py --source-dir archive/sources --llm --review-dir review/current

# Inspect and edit review/current/claims.jsonl
# Set "review_status": "accepted" or "rejected" on each claim

# Generate report from accepted claims only
py scripts/report_from_review.py --review-dir review/current --as-of $TODAY
```

---

## Persist and compare runs

```powershell
# Save current run to SQLite
py scripts/persist_run.py --as-of $TODAY --source seed

# List saved runs
py scripts/persist_run.py --list

# Compare two most recent runs
py scripts/compare_runs.py --output reports/${TODAY}_run_diff.md

# Historical trend report
py scripts/historical_trends.py --as-of $TODAY
```

---

## API

The HTTP server exposes a JSON API:

| Endpoint | Description |
|---|---|
| `GET /api/health` | Service status and evidence freshness |
| `GET /api/bottleneck-radar` | Scored technologies: current, emerging, declining |
| `GET /api/technology-radar` | Attention scores and momentum for all technologies |
| `GET /api/bottlenecks/{technology}` | Full detail: score, breakdown, evidence, counterarguments |
| `GET /api/theses?technology=Power` | LLM-generated investment thesis for a technology |
| `GET /api/coverage` | Evidence coverage audit against policy targets |
| `GET /api/evidence-audit` | Traceability check for source URLs and evidence quotes |
| `GET /api/acquisition-plan` | Recommended sources to fill evidence gaps |
| `GET /api/expert-signal` | Signal from designated expert sources |

---

## Test

```powershell
pytest -q
pytest tests/test_evidence_audit.py -q
```

---

## Current limitations

This is an early-stage system. Known gaps:

**Evidence coverage** — Some technologies may show `insufficient_evidence` if the extracted claim set does not yet cover all three required claim groups (demand, constraint, counterargument) from at least two independent sources. Running a fresh `fetch_feeds.py` + `extract_claims.py` cycle improves coverage over time.

**Low evidence is not proof of no bottleneck** — A low attention score usually means the current public-source set is thin or the technology is not yet prominent in the collected materials. It should be read as a coverage and popularity signal, not as proof that the technology cannot become a bottleneck.

**Ingestion** — The system is not an automated crawler. Evidence is fetched and extracted on manual trigger via `fetch_feeds.py` + `extract_claims.py`. A scheduled pipeline is the next production step.

**LLM extraction review** — LLM-extracted claims are drafts until reviewed. Production reports should use accepted claims whose evidence quotes trace back to stored source text.

**Attention momentum** — The 30-day growth metric is derived from evidence publication dates, not a real historical time-series. When history is thin, the UI reports `insufficient history` instead of treating a sparse data set as a real trend.

**Expert sources** — SemiAnalysis and other expert newsletters are not yet in the default feed list. Adding them will materially improve signal quality.
