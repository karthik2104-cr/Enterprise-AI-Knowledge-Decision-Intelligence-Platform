from __future__ import annotations

import json
import re
from typing import Any

from app.core.prompts import render_prompt
from app.providers.llm import get_llm_provider
from app.retrieval.service import Hit
from app.schemas.common import Claim, StructuredAnswer


def verify_answer(
    answer: StructuredAnswer,
    hits: list[Hit],
    db_facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    chunk_ids = {h.chunk_id for h in hits}
    doc_names = {h.document_name.lower() for h in hits}
    corpus = " ".join(h.content.lower() for h in hits)
    if db_facts:
        corpus += " " + json.dumps(db_facts).lower()
    issues: list[str] = []
    supported_claims = 0
    for claim in answer.claims:
        tokens = [t for t in re.findall(r"[a-z0-9]{4,}", claim.text.lower())]
        overlap = sum(1 for t in tokens if t in corpus)
        ok = overlap >= max(1, int(0.25 * len(tokens))) if tokens else bool(hits or db_facts)
        claim.supported = ok
        if not ok:
            issues.append(f"Claim lacks overlapping evidence: {claim.text[:120]}")
        else:
            supported_claims += 1
        for ev in claim.evidence:
            if ev.chunk_id and ev.chunk_id not in chunk_ids:
                issues.append("Citation references a chunk that was not retrieved.")
            if ev.document and ev.document.lower() not in doc_names and ev.document.lower() not in {
                "structured metrics",
                "database",
            }:
                issues.append(f"Citation document not in retrieved set: {ev.document}")
    contradiction = _detect_conflict(hits)
    if contradiction:
        issues.append(contradiction)
        answer.uncertainty.append(contradiction)
    status = "pass"
    if not hits and not db_facts:
        status = "insufficient_evidence"
    elif issues:
        status = "uncertain"
    groundedness = 0.0 if not answer.claims else supported_claims / max(len(answer.claims), 1)
    if answer.answer.lower().startswith("i couldn't find sufficient evidence"):
        status = "insufficient_evidence"
        groundedness = 1.0
    try:
        notes = get_llm_provider().complete_json(
            "Verifier",
            render_prompt("verifier.txt", answer=answer.answer, issues="; ".join(issues) or "none"),
        )
    except Exception:
        notes = {}
    result = {
        "status": status,
        "issues": issues,
        "groundedness": round(groundedness, 3),
        "claims_checked": len(answer.claims),
        "supported_claims": supported_claims,
        "guarantees_truth": False,
        "notes": notes.get("notes") if isinstance(notes, dict) else "heuristic verification",
    }
    answer.verification = result
    if status == "uncertain":
        answer.confidence = min(answer.confidence, 0.45)
        if issues:
            answer.uncertainty = list(dict.fromkeys(answer.uncertainty + issues[:3]))
    return result


def _detect_conflict(hits: list[Hit]) -> str | None:
    numbers: dict[str, list[str]] = {}
    for hit in hits:
        for match in re.findall(r"(revenue[^\n.]{0,40}?\$?[0-9]+(?:\.[0-9]+)?\s*(?:million|m)?)", hit.content.lower()):
            numbers.setdefault(match[:24], []).append(hit.document_name)
    return None
