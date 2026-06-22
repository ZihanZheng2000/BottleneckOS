"""LLM-powered claim extraction — supports OpenAI and Anthropic.

Auto-detects provider from .env:
  OPENAI_API_KEY     → uses OpenAI (default model: gpt-4o-mini)
  ANTHROPIC_API_KEY  → uses Anthropic (default model: claude-haiku-4-5)

If both keys are present, set PREFERRED_LLM_PROVIDER=openai or anthropic to pick.

Requires: pip install openai        (for OpenAI)
          pip install anthropic     (for Anthropic)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .extractor import _stable_id, extract_document_and_claims as _kw_extract
from .models import Claim, Document, Technology
from .seed_data import TECHNOLOGIES

_ROOT = Path(__file__).resolve().parent.parent

_VALID_CLAIM_TYPES = frozenset({
    "demand_signal",
    "capacity_signal",
    "technical_constraint",
    "infrastructure_constraint",
    "substitution_signal",
    "counterargument",
})

DEFAULT_MODEL = {
    "openai": "gpt-5",
    "anthropic": "claude-haiku-4-5",
}

CATEGORIES = (
    "Compute", "Memory", "Packaging", "Networking",
    "Optical", "Power", "Cooling", "Data Center",
)

_SYSTEM = """\
You are an industrial intelligence analyst specializing in AI infrastructure bottleneck transitions.

Already-tracked technologies (use these EXACT names when the text is about one of them):
{technologies}

Read the source text first and decide what it is actually about — do not force-fit it into the
tracked list above. Extract every specific, factual claim about a technology or component that
could become an AI-infrastructure bottleneck:
- If it matches a tracked technology, use that exact name.
- If it describes a distinct technology or component NOT in the tracked list (a new chip,
  material, protocol, or infrastructure element), extract it anyway with its own concise
  canonical name and best-fit category — but only if the source text itself ties it explicitly
  to AI infrastructure, AI data centers, or AI compute demand/supply. Do not drop a real signal
  just because nothing in the tracked list matches it — new bottlenecks are exactly what this
  system is meant to surface.
- Do NOT register a new technology from material that is generically about energy, semiconductors,
  commodities, shipping, or industrial policy with no explicit AI/data-center connection (e.g.
  nuclear weapons material production, general fuel and commodity markets, oil refining, freight
  logistics). Skip those claims entirely rather than inventing an out-of-scope entry.

Return ONLY valid JSON — no markdown, no explanation, no code fences. Schema:
{{
  "claims": [
    {{
      "technology": "<exact tracked name, or a new concise canonical technology/component name>",
      "technology_category": "<one of: {categories}>",
      "claim_type": "<demand_signal|capacity_signal|technical_constraint|infrastructure_constraint|substitution_signal|counterargument>",
      "claim": "<concise 1-2 sentence factual claim, max 220 characters>",
      "evidence_quote": "<verbatim sentence(s) from the source>",
      "confidence": <0.0-1.0>,
      "impact": <0-100>
    }}
  ]
}}

Rules:
- Only include claims where the technology is explicitly mentioned.
- Skip generic, speculative, or marketing statements with no factual grounding.
- counterargument: statements that reduce bottleneck severity — supply improving, alternatives emerging, problem overstated, demand slowing, technology maturing faster than expected. Look hard for these even in bullish documents; they are often buried ("while supply is tight, we expect...") and are critical for balanced analysis.
- confidence: 0.92 for government/regulatory, 0.87 for SEC filings/earnings, 0.76 for analyst reports, 0.65 for news.
- impact: 85+ critical supply/demand constraints, 60-84 significant signals, below 60 weak signals.
- Max 20 claims per document.\
"""


# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------

def _load_dotenv() -> dict[str, str]:
    env_path = _ROOT / ".env"
    result: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
    return result


def _get_key(name: str, dotenv: dict[str, str]) -> str:
    return os.environ.get(name, "") or dotenv.get(name, "")


def detect_provider(preferred: str = "auto") -> tuple[str, str]:
    """Return (provider_name, api_key). Raises if nothing found."""
    dotenv = _load_dotenv()
    openai_key = _get_key("OPENAI_API_KEY", dotenv)
    anthropic_key = _get_key("ANTHROPIC_API_KEY", dotenv)

    if preferred == "openai":
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY not found in .env or environment")
        return "openai", openai_key
    if preferred == "anthropic":
        if not anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY not found in .env or environment")
        return "anthropic", anthropic_key

    # auto: check PREFERRED_LLM_PROVIDER first, then whichever key exists
    env_pref = _get_key("PREFERRED_LLM_PROVIDER", dotenv).lower()
    if env_pref in ("openai", "anthropic"):
        return detect_provider(env_pref)
    if openai_key:
        return "openai", openai_key
    if anthropic_key:
        return "anthropic", anthropic_key
    raise RuntimeError(
        "No LLM API key found. Add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env"
    )


# ---------------------------------------------------------------------------
# LLM call (unified interface)
# ---------------------------------------------------------------------------

def _make_client(provider: str, api_key: str):
    if provider == "openai":
        try:
            import openai
        except ImportError:
            raise ImportError("Run: pip install openai")
        return openai.OpenAI(api_key=api_key)
    if provider == "anthropic":
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: pip install anthropic")
        return anthropic.Anthropic(api_key=api_key)
    raise ValueError(f"Unknown provider: {provider}")


def _call_llm(provider: str, client, model: str, system: str, user_text: str) -> str:
    if provider == "openai":
        kwargs: dict = {
            "model": model,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
        }
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            if "temperature" in str(exc):
                kwargs.pop("temperature")
                response = client.chat.completions.create(**kwargs)
            else:
                raise
        return response.choices[0].message.content or "{}"

    if provider == "anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            temperature=0.1,
            messages=[{"role": "user", "content": user_text}],
        )
        return response.content[0].text if response.content else "{}"

    raise ValueError(f"Unknown provider: {provider}")


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Find outermost { ... }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------

def _build_tech_list(technologies: list[Technology]) -> str:
    return "\n".join(
        f"- {t.name} (aliases: {', '.join(t.aliases) or 'none'}, category: {t.category})"
        for t in technologies
    )


def _make_tech_lookup(technologies: list[Technology]) -> dict[str, Technology]:
    lookup: dict[str, Technology] = {}
    for t in technologies:
        lookup[t.name.lower()] = t
        for alias in t.aliases:
            lookup[alias.lower()] = t
    return lookup


def _register_technology(
    name: str,
    category: str,
    technologies: list[Technology],
    tech_lookup: dict[str, Technology],
) -> Technology:
    """Judge step: the text introduced a technology outside the tracked ontology.

    Registers it as provisional (instead of dropping the signal) and appends it to the
    caller's `technologies` list in place so later documents in the same run, and the
    returned Repository, see it too.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    tech_id = f"tech_{slug}" if slug else _stable_id("tech", name.lower())
    technology = Technology(tech_id, name, category if category in CATEGORIES else "Other", (), "provisional")
    technologies.append(technology)
    tech_lookup[name.lower()] = technology
    return technology


_ITEM_HEADING = re.compile(r"item\s+(\d{1,2}[a-c]?)[.\s]", re.IGNORECASE)
_PRIORITY_SECTIONS = ("1A", "7")  # Item 1A Risk Factors, Item 7 MD&A


def _select_extraction_text(document: Document, max_chars: int) -> str:
    """Pick the text sent to the LLM.

    Large SEC filings open with pages of XBRL tag dumps and a table of
    contents before any prose starts, so blindly truncating to max_chars
    sends mostly noise and never reaches Item 1A/7 — the sections with the
    demand/risk language claims actually need. Locate those sections instead
    when the document is too big to send whole; everything else (8-Ks, RSS
    articles, blog posts) is short enough that this never triggers.
    """
    text = document.clean_text
    if len(text) <= max_chars or document.source_type != "sec_filing":
        return text[:max_chars]

    matches = [(m.start(), m.group(1).upper()) for m in _ITEM_HEADING.finditer(text)]
    best: dict[str, tuple[int, int]] = {}
    for i, (start, label) in enumerate(matches):
        if label not in _PRIORITY_SECTIONS:
            continue
        next_start = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        gap = next_start - start
        # Table-of-contents entries are followed almost immediately by the next
        # "Item N" marker; the real section heading precedes a long prose run.
        if gap > 5000 and gap > best.get(label, (0, 0))[1]:
            best[label] = (start, gap)

    if not best:
        return text[:max_chars]

    budget = max_chars // len(best)
    ordered = sorted(best.values(), key=lambda value: value[0])
    pieces = [text[start : start + min(gap, budget)] for start, gap in ordered]
    return "\n\n".join(pieces)


def extract_claims_with_llm(
    document: Document,
    technologies: list[Technology],
    *,
    provider: str,
    client,
    model: str,
    max_chars: int = 40_000,
) -> list[Claim]:
    system = _SYSTEM.format(technologies=_build_tech_list(technologies), categories=", ".join(CATEGORIES))
    text = _select_extraction_text(document, max_chars)

    raw_text = _call_llm(provider, client, model, system, f"Source text:\n\n{text}")
    raw = _parse_json_response(raw_text)

    tech_lookup = _make_tech_lookup(technologies)
    claims: list[Claim] = []
    seen: set[tuple] = set()

    for item in raw.get("claims", []):
        tech_name = str(item.get("technology", "")).strip()
        if not tech_name:
            continue
        technology = tech_lookup.get(tech_name.lower())
        if technology is None:
            category = str(item.get("technology_category", "")).strip()
            technology = _register_technology(tech_name, category, technologies, tech_lookup)
        claim_type = str(item.get("claim_type", "")).strip()
        if claim_type not in _VALID_CLAIM_TYPES:
            continue
        claim_text = str(item.get("claim", "")).strip()[:220]
        quote = str(item.get("evidence_quote", "")).strip()
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.75))))
        impact = max(0, min(100, int(item.get("impact", 70))))

        key = (technology.id, claim_type, claim_text)
        if key in seen:
            continue
        seen.add(key)

        claim_id = _stable_id("claim", document.id, technology.id, claim_type, claim_text)
        claims.append(Claim(claim_id, document.id, technology.id, claim_type, claim_text, quote, confidence, impact))

    return claims


# ---------------------------------------------------------------------------
# Directory-level extraction (same interface as extractor.py)
# ---------------------------------------------------------------------------

def extract_repository_from_directory(
    source_dir: Path,
    technologies: list[Technology] | None = None,
    *,
    provider: str = "auto",
    model: str | None = None,
    max_chars: int = 40_000,
    fallback_to_keywords: bool = True,
):
    from .repository import Repository

    provider_name, api_key = detect_provider(provider)
    effective_model = model or DEFAULT_MODEL[provider_name]
    client = _make_client(provider_name, api_key)

    print(f"Provider: {provider_name}  Model: {effective_model}  Max chars/doc: {max_chars:,}")

    technologies = list(technologies or TECHNOLOGIES)
    documents: list[Document] = []
    all_claims: list[Claim] = []

    for path in sorted(source_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        document, kw_claims = _kw_extract(path, technologies)
        documents.append(document)
        print(f"  [llm] {path.name} ...", end=" ", flush=True)
        try:
            before = len(technologies)
            claims = extract_claims_with_llm(
                document, technologies,
                provider=provider_name, client=client, model=effective_model, max_chars=max_chars,
            )
            discovered = technologies[before:]
            suffix = f" (+{len(discovered)} new: {', '.join(t.name for t in discovered)})" if discovered else ""
            print(f"{len(claims)} claims{suffix}")
        except Exception as exc:
            if fallback_to_keywords:
                print(f"failed ({exc}) -> keyword fallback: {len(kw_claims)} claims")
                claims = kw_claims
            else:
                print(f"failed: {exc}")
                claims = []
        all_claims.extend(claims)

    return Repository(technologies, documents, all_claims)
