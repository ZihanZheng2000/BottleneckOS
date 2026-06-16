# Source Input Format

The preferred workflow uses real public RSS/API feeds from `sources/feeds.txt`.
For one-off URL ingestion, use `sources/manifest.real.txt`, which contains real
public source URLs.

If you manually add source text files, use Markdown files with a metadata header:

```markdown
title: NVIDIA 800 VDC Architecture Will Power the Next Generation of AI Factories
source_name: NVIDIA
source_type: technical_blog
published_at: 2025-05-20
url: https://developer.nvidia.com/blog/nvidia-800-v-hvdc-architecture-will-power-the-next-generation-of-ai-factories/
reliability_weight: 0.9
---
Paste quoted or copied source text here.
```

Then run:

```powershell
py scripts/ingest_sources.py --source-dir sources
```

The extractor is manual-triggered, not scheduled. It turns source text into Document and Claim records automatically, then generates a report.

## RSS Feed Pipeline (recommended)

The primary workflow uses configured RSS feeds. Edit `sources/feeds.txt` to add or remove feeds, then:

```powershell
# Fetch all configured feeds
py scripts/fetch_feeds.py --feeds sources/feeds.txt --archive-dir archive/sources

# Extract claims with LLM
py scripts/extract_claims.py --source-dir archive/sources --llm --auto-accept
```

## URL Manifest

For URL ingestion from real public pages, run:

```powershell
py scripts/fetch_sources.py --manifest sources/manifest.real.txt --archive-dir archive/sources
py scripts/ingest_sources.py --source-dir archive/sources
```

HTML and text sources are converted into archived Markdown. PDF files are archived but marked as requiring a PDF parser before extraction.
