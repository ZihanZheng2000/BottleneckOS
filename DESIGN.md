# Bottleneck OS Design

## 1. Product Positioning

Bottleneck OS is an AI-native industrial intelligence system for discovering bottleneck transitions before consensus.

It is not a trading system, stock screener, portfolio tool, or technical analysis product. The core user is an industrial intelligence analyst who wants to understand where AI infrastructure constraints are moving: compute, memory, networking, power, cooling, packaging, optical, and data centers.

The product should answer five questions:

1. What are serious AI infrastructure people talking about now?
2. Which technologies are gaining or losing attention?
3. Which technologies are likely becoming bottlenecks?
4. What evidence explains the bottleneck thesis?
5. Where does the system disagree with consensus?

## 2. MVP User Experience

The MVP should feel like an analyst workstation, not a stock terminal.

Primary screens:

1. Technology Radar
   - Ranked technology list.
   - Current attention score.
   - 30-day and 90-day attention growth.
   - Momentum label: declining, stable, rising, explosive.
   - Evidence count by source type.

2. Bottleneck Radar
   - Top current bottlenecks.
   - Emerging bottlenecks.
   - Declining bottlenecks.
   - Bottleneck score, confidence, expected timeline.
   - Drill-down into constraints and supporting evidence.

3. Thesis Workspace
   - Select one bottleneck candidate.
   - View generated research thesis.
   - Inspect evidence, counterarguments, assumptions, timeline, affected companies, and related technologies.
   - Export thesis as Markdown.

4. Consensus Gap
   - Compare internal bottleneck score with proxy consensus score.
   - Surface underappreciated, overhyped, and misunderstood bottlenecks.

## 3. Domain Ontology

The ontology is the backbone of the system. Start simple and expand only when needed.

Core entity types:

- Technology: GPU, CPU, HBM, CPO, silicon photonics, liquid cooling, substations, power transformers.
- Component: accelerator, switch ASIC, optical transceiver, retimer, interposer, CDU, chiller.
- Company: NVIDIA, Broadcom, Arista, Micron, SK Hynix, TSMC, Lumentum, Coherent.
- Constraint: capacity, yield, lead time, capex, power availability, thermal density, packaging throughput.
- Source: article, transcript, interview, public post, research report, earnings call, conference talk.
- Signal: mention, claim, forecast, risk, supply constraint, demand driver, capex change, product roadmap.

Minimum technology taxonomy:

- Compute: GPU, CPU, accelerator, inference ASIC.
- Memory: HBM, DRAM, SRAM, GDDR.
- Packaging: CoWoS, advanced packaging, interposer, substrates.
- Networking: Ethernet, InfiniBand, switch ASIC, optical module.
- Optical: CPO, silicon photonics, EML, LPO, pluggable optics.
- Power: grid interconnect, transformer, substation, backup generation, power distribution.
- Cooling: air cooling, liquid cooling, immersion, CDU, heat exchanger.
- Data Center: land, permits, construction, rack density, colocation.

## 4. Data Pipeline

### 4.1 Ingestion

MVP sources should be limited and high quality.

Priority sources:

- SemiAnalysis articles and public posts.
- Serenity-style research notes if available locally.
- Company earnings transcripts.
- Investor day transcripts and conference presentations.
- NVIDIA, Broadcom, Arista, Micron, SK Hynix, TSMC, Lumentum, Coherent public materials.
- Selected interviews and conference talks.

Each document is stored as:

```json
{
  "id": "doc_...",
  "source_name": "SemiAnalysis",
  "source_type": "article",
  "url": "https://...",
  "published_at": "2026-01-15",
  "ingested_at": "2026-01-16T10:30:00Z",
  "title": "...",
  "author": "...",
  "raw_text": "...",
  "clean_text": "...",
  "reliability_weight": 0.9
}
```

### 4.2 Extraction

Use an LLM extraction pass plus deterministic normalization.

Extract:

- mentioned technologies
- mentioned companies
- bottleneck claims
- demand signals
- capacity signals
- lead-time claims
- roadmap changes
- infrastructure dependencies
- counterarguments
- dates and timelines

Claim object:

```json
{
  "id": "claim_...",
  "doc_id": "doc_...",
  "technology": "CPO",
  "claim_type": "capacity_constraint",
  "claim": "CPO adoption is limited by packaging, reliability, and ecosystem readiness.",
  "evidence_quote": "...",
  "source_type": "conference_transcript",
  "published_at": "2026-02-04",
  "confidence": 0.78
}
```

### 4.3 Storage

Use Postgres for structured data and pgvector for semantic retrieval.

Core tables:

- documents
- entities
- entity_aliases
- document_entities
- claims
- technology_daily_metrics
- bottleneck_scores
- generated_theses

For MVP simplicity, use one app database and one background worker. Avoid distributed architecture until ingestion volume forces it.

## 5. Scoring System

Scores should be explainable. Every score needs contributing factors and evidence links.

### 5.1 Attention Score

Attention score measures how much high-quality discussion a technology receives.

Suggested formula:

```text
attention_score =
  weighted_mentions
  + unique_source_bonus
  + source_quality_bonus
  + recency_bonus
  + evidence_depth_bonus
```

Inputs:

- mention frequency
- number of distinct sources
- source reliability
- recency decay
- number of substantive claims
- source diversity across analyst, company, conference, earnings, research

Normalize to 0-100 by comparing against all tracked technologies over the last 90 days.

Momentum:

```text
30d_growth = (attention_30d - previous_attention_30d) / previous_attention_30d
90d_growth = (attention_90d - previous_attention_90d) / previous_attention_90d
momentum = f(30d_growth, 90d_growth, source_diversity_growth)
```

Momentum labels:

- declining: growth < -15%
- stable: -15% to +15%
- rising: +15% to +40%
- explosive: > +40% with at least three independent source types

### 5.2 Bottleneck Score

Bottleneck score estimates constraint severity.

Factors:

```text
bottleneck_score =
  0.25 * demand_growth
  + 0.20 * capacity_tightness
  + 0.15 * lead_time
  + 0.15 * technical_difficulty
  + 0.10 * substitution_difficulty
  + 0.10 * infrastructure_dependency
  + 0.05 * evidence_quality
```

All factors are 0-100.

Factor interpretation:

- Demand Growth: downstream demand acceleration.
- Capacity Tightness: supply limits, yields, capex lag, construction lag.
- Lead Time: time needed to add capacity or deploy alternatives.
- Technical Difficulty: engineering complexity and maturity risk.
- Substitution Difficulty: how hard it is to route around this bottleneck.
- Infrastructure Dependency: dependency on external physical systems such as grid, permits, fabs, packaging, logistics.
- Evidence Quality: diversity and credibility of supporting evidence.

### 5.3 Emerging Bottleneck Score

Emerging bottlenecks are not simply high score items. They are accelerating before consensus.

```text
emerging_score =
  bottleneck_score
  * attention_growth_multiplier
  * consensus_gap_multiplier
  * novelty_multiplier
```

This helps avoid repeatedly saying "GPU" when the interesting transition has moved to HBM, networking, power, or cooling.

### 5.4 Consensus Proxy

Consensus is hard to measure directly. For MVP, approximate it from broad attention and market narrative.

Consensus proxy inputs:

- mainstream media mentions
- earnings-call question frequency
- broad financial-news coverage
- sell-side style report titles, if available
- social/public post volume from non-specialist sources

Contrarian gap:

```text
contrarian_gap = system_bottleneck_score - consensus_proxy_score
```

Classifications:

- Underappreciated: high bottleneck score, low consensus proxy.
- Overhyped: high consensus proxy, weak bottleneck evidence.
- Misunderstood: high attention, but evidence points to a different underlying constraint.

## 6. Evidence Engine

The Evidence Engine must prevent unsupported score output.

For every bottleneck thesis, require:

- at least one demand-side evidence item
- at least one supply/capacity evidence item
- at least one technical or infrastructure evidence item
- at least one counterargument or disconfirming signal

Evidence pack format:

```json
{
  "technology": "Power",
  "question": "Why is power becoming a bottleneck for AI infrastructure?",
  "supporting_evidence": [
    {
      "type": "infrastructure",
      "source": "Company transcript",
      "date": "2026-03-01",
      "claim": "...",
      "quote": "...",
      "weight": 0.82
    }
  ],
  "counterarguments": [
    {
      "claim": "Some hyperscalers can secure power through long-term utility agreements.",
      "evidence": "..."
    }
  ],
  "confidence": 0.76,
  "timeline": "12-36 months"
}
```

## 7. Thesis Generator

Generated reports should be structured, restrained, and evidence-led.

Markdown template:

```markdown
# Bottleneck Thesis: {Technology}

## Summary
{One-paragraph thesis}

## Why This Matters
{Industrial consequence, not stock implication}

## Key Evidence
1. {Evidence}
2. {Evidence}
3. {Evidence}

## Bottleneck Mechanics
{Demand growth, capacity limits, lead time, substitution difficulty}

## Timeline
{Expected emergence window}

## Affected Technologies
{Related technologies}

## Affected Companies
{Companies exposed operationally or strategically}

## Counterarguments
{Best opposing view}

## What Would Change Our Mind
{Disconfirming evidence}

## Confidence
{Score and reason}
```

## 8. Recommended MVP Stack

Backend:

- Python
- FastAPI
- Postgres + pgvector
- SQLAlchemy or SQLModel
- Celery/RQ or a simple APScheduler worker for MVP

AI:

- LLM extraction for claims and entities
- Embeddings for document retrieval
- RAG for thesis generation
- Strict JSON schemas for extraction outputs

Frontend:

- Next.js or Vite React
- Table-first analyst UI
- Detail drawers for evidence
- Markdown thesis viewer/export

Deployment:

- Docker Compose for MVP
- One web container
- One worker container
- One Postgres container

## 9. Agent and Module Design

MVP services:

1. Ingestion Service
   - Fetches or imports documents.
   - Cleans text.
   - De-duplicates by URL, title, and text hash.

2. Extraction Service
   - Runs LLM extraction.
   - Normalizes entities to ontology.
   - Stores claims and evidence.

3. Metrics Service
   - Computes daily attention metrics.
   - Computes growth and momentum.
   - Computes bottleneck scores.

4. Evidence Service
   - Retrieves evidence by technology and claim type.
   - Builds evidence packs.
   - Checks minimum evidence requirements.

5. Thesis Service
   - Generates Markdown reports.
   - Stores generated thesis versions.
   - Links every claim back to evidence.

6. API Service
   - `/technologies/radar`
   - `/bottlenecks/radar`
   - `/bottlenecks/{technology}`
   - `/bottlenecks/{technology}/evidence`
   - `/theses/generate`
   - `/theses/{id}`

## 10. MVP Data Flow

```text
Source documents
  -> ingestion
  -> text cleaning
  -> entity and claim extraction
  -> ontology normalization
  -> document/entity/claim storage
  -> daily metric calculation
  -> bottleneck scoring
  -> evidence pack creation
  -> thesis generation
  -> dashboard and markdown report
```

## 11. First Implementation Milestone

Build a narrow vertical slice around five technologies:

- HBM
- Networking
- CPO
- Power
- Cooling

And ten to twenty seed documents.

Milestone output:

- Import seed documents manually from Markdown/text files.
- Extract entities and bottleneck claims.
- Compute attention and bottleneck scores.
- Show a radar table.
- Generate one thesis report with linked evidence.

This will prove the core loop before investing in source automation.

## 12. Four-Week Build Plan

Week 1: Foundations

- Create ontology seed file.
- Create Postgres schema.
- Build document import CLI.
- Build entity and claim extraction schema.
- Import 10 seed documents.

Week 2: Metrics

- Implement attention score.
- Implement bottleneck score.
- Implement daily metric snapshots.
- Build backend endpoints.

Week 3: Evidence and Thesis

- Implement evidence pack retrieval.
- Add evidence minimum checks.
- Implement thesis generator.
- Store thesis versions.

Week 4: Analyst UI

- Build Technology Radar.
- Build Bottleneck Radar.
- Build bottleneck detail view.
- Build Markdown thesis export.
- Add basic admin page for source/document inspection.

## 13. Non-Goals

Do not build these in the MVP:

- stock price integration
- brokerage integration
- portfolio tracking
- automated trading
- broad market news firehose
- social media sentiment firehose
- complex multi-tenant permissions
- real-time streaming architecture

## 14. Design Principles

- Evidence before score.
- Explain mechanism, not just trend.
- Track constraint transitions, not tickers.
- Prefer fewer high-quality sources over noisy volume.
- Make every generated thesis falsifiable.
- Separate attention from bottleneck severity.
- Treat consensus as a measured external narrative, not as truth.

