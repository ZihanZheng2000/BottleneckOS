"""Small standard-library HTTP API for Bottleneck OS."""

from __future__ import annotations

import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .acquisition import build_acquisition_plan
from .coverage import coverage_summary, source_coverage, technology_policy_coverage
from .evidence_audit import audit_evidence_traceability
from .expert_signal import expert_signal_by_technology, expert_signal_summary, expert_source_coverage
from .policy import SOURCE_UNIVERSE, TECHNOLOGY_UNIVERSE
from .repository import build_seed_repository
from .review import review_claim_records, review_summary, update_claim_review
from .scoring import bottleneck_radar, technology_detail, technology_radar
from .thesis import generate_thesis

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
REVIEW_DIR = ROOT / "review" / "current"


class BottleneckHandler(BaseHTTPRequestHandler):
    repo = build_seed_repository()
    review_dir = REVIEW_DIR

    @property
    def as_of(self) -> date:
        return date.today()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def _send_text(self, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in {"/", "/index.html"}:
                self._send_text((WEB_DIR / "index.html").read_text(encoding="utf-8"), "text/html; charset=utf-8")
            elif path == "/api/health":
                newest = max((doc.published_at for doc in self.repo.documents), default=None)
                self._send_json({
                    "ok": True,
                    "service": "Bottleneck OS",
                    "as_of": self.as_of.isoformat(),
                    "newest_evidence": newest.isoformat() if newest else None,
                    "evidence_age_days": (self.as_of - newest).days if newest else None,
                })
            elif path == "/api/technology-radar":
                self._send_json(technology_radar(self.repo, self.as_of))
            elif path == "/api/bottleneck-radar":
                self._send_json(bottleneck_radar(self.repo, self.as_of))
            elif path == "/api/coverage":
                self._send_json(
                    {
                        "summary": coverage_summary(self.repo),
                        "sources": source_coverage(self.repo),
                        "technologies": technology_policy_coverage(self.repo),
                    }
                )
            elif path == "/api/acquisition-plan":
                self._send_json(
                    {
                        "as_of": self.as_of.isoformat(),
                        "items": build_acquisition_plan(self.repo),
                    }
                )
            elif path == "/api/expert-signal":
                self._send_json(
                    {
                        "summary": expert_signal_summary(self.repo),
                        "sources": expert_source_coverage(self.repo),
                        "technologies": expert_signal_by_technology(self.repo),
                    }
                )
            elif path == "/api/evidence-audit":
                self._send_json(audit_evidence_traceability(self.repo))
            elif path == "/api/policy/sources":
                self._send_json([source.__dict__ for source in SOURCE_UNIVERSE])
            elif path == "/api/policy/technologies":
                self._send_json([technology.__dict__ for technology in TECHNOLOGY_UNIVERSE])
            elif path == "/api/review":
                self._send_json(
                    {
                        "summary": review_summary(self.review_dir),
                        "claims": review_claim_records(self.review_dir, limit=50),
                    }
                )
            elif path.startswith("/api/bottlenecks/"):
                technology = unquote(path.removeprefix("/api/bottlenecks/"))
                self._send_json(technology_detail(self.repo, technology, self.as_of))
            elif path == "/api/theses":
                query = parse_qs(parsed.query)
                technology = query.get("technology", ["Power"])[0]
                self._send_json(
                    {
                        "id": f"thesis_{technology.lower().replace(' ', '_')}",
                        "technology": technology,
                        "markdown": generate_thesis(self.repo, technology, self.as_of),
                    }
                )
            else:
                self._send_json({"error": "Not found"}, 404)
        except KeyError as exc:
            self._send_json({"error": str(exc)}, 404)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, 400)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)

    def _ingest(self, payload: dict) -> dict:
        from collections import Counter
        from .extractor import (
            _stable_id, split_sentences, technology_matches,
            classify_claim_type, infer_claim, IMPACT_BY_TYPE,
        )
        from .fetcher import fetch_url, html_to_text
        from .models import Claim, Document
        from .repository import Repository

        url = payload.get("url", "").strip()
        raw_text = payload.get("text", "").strip()
        filename = payload.get("filename", "upload.txt")

        if not url and not raw_text:
            raise ValueError("Either 'url' or 'text' is required")

        source_name = payload.get("source_name", "").strip()
        source_type = payload.get("source_type", "news_article")
        title = payload.get("title", "").strip()
        published_at_str = payload.get("published_at", date.today().isoformat())
        reliability_weight = float(payload.get("reliability_weight", 0.8))
        published_at = date.fromisoformat(published_at_str)

        if url:
            content_bytes, content_type = fetch_url(url)
            if "pdf" in content_type.lower():
                raise ValueError("PDF files are not supported — paste the text content instead")
            decoded = content_bytes.decode("utf-8", errors="replace")
            content = html_to_text(decoded) if "html" in content_type.lower() else decoded
            if not source_name:
                source_name = urlparse(url).netloc
            if not title:
                title = url
            doc_url = url
        else:
            content = raw_text
            if not source_name:
                source_name = Path(filename).stem
            if not title:
                title = filename
            doc_url = f"file://{filename}"

        content = content.strip()
        if not content:
            raise ValueError("No content to analyze")

        doc_id = _stable_id("doc", source_name, title, doc_url)
        document = Document(
            doc_id, title, source_name, source_type, published_at, doc_url, content, reliability_weight
        )

        if any(d.id == doc_id for d in self.repo.documents):
            raise ValueError(f"This document has already been ingested (id: {doc_id})")

        technologies = list(self.repo.technologies)
        extraction_method = "keyword"
        try:
            from .llm_extractor import detect_provider, _make_client, extract_claims_with_llm, DEFAULT_MODEL
            provider_name, api_key = detect_provider()
            client = _make_client(provider_name, api_key)
            model = DEFAULT_MODEL[provider_name]
            claims = extract_claims_with_llm(
                document, technologies,
                provider=provider_name, client=client, model=model,
            )
            extraction_method = f"{provider_name}/{model}"
        except Exception:
            claims = []
            seen: set = set()
            for sentence in split_sentences(content):
                claim_type = classify_claim_type(sentence)
                if not claim_type:
                    continue
                for tech in technology_matches(sentence, technologies):
                    key = (tech.id, claim_type, sentence)
                    if key in seen:
                        continue
                    seen.add(key)
                    claim_id = _stable_id("claim", doc_id, tech.id, claim_type, sentence)
                    claims.append(Claim(
                        claim_id, doc_id, tech.id, claim_type,
                        infer_claim(sentence, tech, claim_type),
                        sentence, 0.72, IMPACT_BY_TYPE[claim_type],
                    ))

        existing_claim_ids = {c.id for c in self.repo.claims}
        new_claims = [c for c in claims if c.id not in existing_claim_ids]

        BottleneckHandler.repo = Repository(
            technologies,
            list(self.repo.documents) + [document],
            list(self.repo.claims) + new_claims,
        )

        tech_names = {t.id: t.name for t in technologies}
        breakdown = {
            tech_names.get(tid, tid): count
            for tid, count in Counter(c.technology_id for c in new_claims).items()
        }

        return {
            "document_id": doc_id,
            "source_name": source_name,
            "extraction_method": extraction_method,
            "claims_extracted": len(new_claims),
            "technology_breakdown": breakdown,
        }

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/ingest":
                self._send_json(self._ingest(self._read_json_body()))
            elif path.startswith("/api/review/claims/"):
                claim_id = unquote(path.removeprefix("/api/review/claims/"))
                payload = self._read_json_body()
                updated = update_claim_review(
                    self.review_dir,
                    claim_id,
                    str(payload.get("review_status", "")),
                    payload.get("reviewer_note"),
                )
                self._send_json(
                    {
                        "claim": updated,
                        "summary": review_summary(self.review_dir),
                    }
                )
            else:
                self._send_json({"error": "Not found"}, 404)
        except KeyError as exc:
            self._send_json({"error": str(exc)}, 404)
        except FileNotFoundError as exc:
            self._send_json({"error": str(exc)}, 404)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, 400)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)


def run(host: str = "127.0.0.1", port: int = 8000, review_dir: str | None = None) -> None:
    if review_dir:
        from pathlib import Path
        from .repository import Repository
        from .review import load_review_repository
        seed = build_seed_repository()
        reviewed = load_review_repository(Path(review_dir), include_statuses={"accepted"})
        # Merge: seed data + review data, deduplicated by id
        seen_docs = {d.id for d in seed.documents}
        seen_claims = {c.id for c in seed.claims}
        seen_techs = {t.id for t in seed.technologies}
        merged_docs = list(seed.documents) + [d for d in reviewed.documents if d.id not in seen_docs]
        merged_claims = list(seed.claims) + [c for c in reviewed.claims if c.id not in seen_claims]
        merged_techs = list(seed.technologies) + [t for t in reviewed.technologies if t.id not in seen_techs]
        repo = Repository(merged_techs, merged_docs, merged_claims)
        BottleneckHandler.repo = repo
        print(f"Seed: {len(seed.documents)} docs, {len(seed.claims)} claims")
        print(f"Review: {len(reviewed.documents)} docs, {len(reviewed.claims)} claims")
        print(f"Merged: {len(repo.documents)} docs, {len(repo.claims)} claims")
    server = ThreadingHTTPServer((host, port), BottleneckHandler)
    print(f"Bottleneck OS running at http://{host}:{port}")
    server.serve_forever()
