# Bottleneck OS MVP Spec

## MVP Goal

Create a working vertical slice that can ingest a small curated document set, extract bottleneck-related signals, rank AI infrastructure technologies, and generate an evidence-backed thesis report.

The MVP is successful if an analyst can ask:

> What bottleneck is emerging in AI infrastructure, and why?

And receive:

- ranked technologies
- bottleneck scores
- growth trends
- linked evidence
- counterarguments
- a Markdown thesis

## Initial Technology Set

Track only these five technologies in the first release:

- HBM
- Networking
- CPO
- Power
- Cooling

## Seed Source Set

Start with 10-20 manually imported documents:

- analyst articles
- earnings-call excerpts
- conference transcripts
- company presentations
- technical interviews

Manual import is acceptable for the MVP. Automated crawling comes later.

## Core Objects

### Document

```json
{
  "id": "doc_001",
  "title": "Example title",
  "source_name": "SemiAnalysis",
  "source_type": "article",
  "published_at": "2026-02-01",
  "url": "https://example.com",
  "clean_text": "...",
  "reliability_weight": 0.9
}
```

### Technology

```json
{
  "id": "tech_power",
  "name": "Power",
  "category": "Power",
  "aliases": ["grid", "electricity", "power availability", "substation"]
}
```

### Claim

```json
{
  "id": "claim_001",
  "doc_id": "doc_001",
  "technology_id": "tech_power",
  "claim_type": "infrastructure_constraint",
  "claim": "Power availability is limiting data center deployment timelines.",
  "evidence_quote": "...",
  "confidence": 0.82
}
```

### Score Snapshot

```json
{
  "technology_id": "tech_power",
  "date": "2026-06-10",
  "attention_score": 84,
  "attention_growth_30d": 0.32,
  "attention_growth_90d": 0.71,
  "momentum": "rising",
  "bottleneck_score": 92,
  "confidence": 0.78
}
```

## API Contract

### `GET /api/technology-radar`

Returns ranked technology attention.

```json
[
  {
    "technology": "CPO",
    "attention_score": 91,
    "growth_30d": 0.48,
    "growth_90d": 0.83,
    "momentum": "explosive",
    "evidence_count": 14
  }
]
```

### `GET /api/bottleneck-radar`

Returns bottleneck rankings.

```json
{
  "current": [
    {
      "technology": "Power",
      "bottleneck_score": 92,
      "confidence": 0.78,
      "timeline": "12-36 months",
      "top_driver": "Grid interconnect and power delivery lead time"
    }
  ],
  "emerging": [],
  "declining": []
}
```

### `GET /api/bottlenecks/{technology}`

Returns score breakdown and evidence.

```json
{
  "technology": "Power",
  "score": 92,
  "breakdown": {
    "demand_growth": 95,
    "capacity_tightness": 91,
    "lead_time": 96,
    "technical_difficulty": 70,
    "substitution_difficulty": 89,
    "infrastructure_dependency": 100,
    "evidence_quality": 84
  },
  "evidence": [],
  "counterarguments": []
}
```

### `POST /api/theses`

Generates and stores a Markdown thesis.

Request:

```json
{
  "technology": "Power"
}
```

Response:

```json
{
  "id": "thesis_001",
  "technology": "Power",
  "markdown": "# Bottleneck Thesis: Power\n..."
}
```

## Scoring Acceptance Rules

A bottleneck score may be shown only if the system has:

- at least 3 total evidence items
- at least 2 independent source names
- at least 1 demand-side signal
- at least 1 supply, capacity, technical, or infrastructure constraint signal
- at least 1 counterargument or uncertainty note

If these are missing, show:

```text
Insufficient evidence
```

Instead of a precise score.

## Frontend Acceptance Criteria

Technology Radar:

- sortable table
- visible attention score and growth
- momentum badge
- click-through to detail view

Bottleneck Radar:

- top current, emerging, and declining sections
- score breakdown
- evidence preview
- confidence and timeline

Thesis View:

- generated Markdown report
- evidence links visible beside claims
- export/copy Markdown action

## Implementation Order

1. Create seed ontology.
2. Add document import.
3. Add extraction schema.
4. Store claims.
5. Compute attention scores.
6. Compute bottleneck scores.
7. Build API endpoints.
8. Build Technology Radar UI.
9. Build Bottleneck Radar UI.
10. Build thesis generation.

## MVP Risks

- Source quality is more important than source volume.
- LLM extraction must be auditable.
- Scores can create false precision if evidence is weak.
- Consensus proxy will be crude in the first version.
- The first UI should optimize analyst trust, not visual flash.

