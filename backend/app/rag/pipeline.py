from __future__ import annotations

import json
import time
from typing import Any

from app.core.prompts import render_prompt
from app.providers.embeddings import tokenize
from app.providers.llm import get_llm_provider, safe_parse_json
from app.retrieval.service import Hit
from app.schemas.common import Claim, EvidenceItem, LatencyMetrics, StructuredAnswer


INSUFFICIENT = "I couldn't find sufficient evidence in the available knowledge base to answer this reliably."


def hits_to_evidence(hits: list[Hit]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for i, hit in enumerate(hits, start=1):
        items.append(
            EvidenceItem(
                document=hit.document_name,
                page=hit.page,
                section=hit.section,
                chunk_id=hit.chunk_id,
                snippet=hit.snippet(),
                score=hit.score,
                retrieval_method=hit.retrieval_method,
                citation_index=i,
            )
        )
    return items


def construct_context(hits: list[Hit]) -> str:
    lines = []
    for i, hit in enumerate(hits, start=1):
        loc = f"p.{hit.page}" if hit.page else "n/a"
        lines.append(f"[{i}] {hit.document_name} ({loc}, {hit.section or 'body'}): {hit.content[:700]}")
    return "\n".join(lines)


def _evidence_for_text(text: str, hits: list[Hit]) -> list[EvidenceItem]:
    tokens = set(tokenize(text))
    ranked: list[tuple[int, Hit]] = []
    for hit in hits:
        overlap = len(tokens.intersection(set(tokenize(hit.content))))
        if overlap:
            ranked.append((overlap, hit))
    ranked.sort(key=lambda x: x[0], reverse=True)
    chosen = [h for _, h in ranked[:2]] or hits[:1]
    return hits_to_evidence(chosen)


def generate_structured_answer(
    question: str,
    hits: list[Hit],
    db_facts: list[dict[str, Any]],
    extra_notes: str = "",
) -> StructuredAnswer:
    started = time.perf_counter()
    llm = get_llm_provider()
    evidence = hits_to_evidence(hits)
    if not hits and not db_facts:
        return StructuredAnswer(
            answer=INSUFFICIENT,
            confidence=0.12,
            uncertainty=["No documents or structured metrics matched this question."],
            sources=[],
            latency=LatencyMetrics(llm_ms=(time.perf_counter() - started) * 1000),
        )
    prompt = render_prompt(
        "rag_answer.txt",
        evidence=construct_context(hits) or "(none)",
        database=json.dumps(db_facts, indent=2) if db_facts else "(none)",
        question=question,
        notes=extra_notes or "(none)",
    )
    raw = llm.complete_json("You return only valid JSON matching the schema.", prompt)
    parsed = safe_parse_json(raw)
    llm_ms = (time.perf_counter() - started) * 1000
    uncertainty = [str(u) for u in parsed.get("uncertainty") or []]
    answer_text = str(parsed.get("answer") or "").strip() or INSUFFICIENT
    claims: list[Claim] = []
    for c in parsed.get("claims") or []:
        text = c.get("text") if isinstance(c, dict) else str(c)
        claims.append(Claim(text=str(text), evidence=_evidence_for_text(str(text), hits) if hits else []))
    if not claims and answer_text != INSUFFICIENT:
        claims = [Claim(text=answer_text[:400], evidence=evidence[:2])]
    try:
        confidence = float(parsed.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.4
        uncertainty.append("The model did not return a numeric confidence value.")
    confidence = min(max(confidence, 0.0), 1.0)
    return StructuredAnswer(
        answer=answer_text,
        confidence=confidence,
        claims=claims,
        sources=evidence,
        uncertainty=uncertainty,
        latency=LatencyMetrics(llm_ms=llm_ms),
    )
