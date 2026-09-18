from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.agents.verifier import verify_answer
from app.core.prompts import load_prompt
from app.database.models import QueryRecord, ResponseRecord, Source
from app.providers.llm import get_llm_provider
from app.rag.pipeline import generate_structured_answer, hits_to_evidence
from app.retrieval.service import Hit, retrieve_with_timing
from app.schemas.common import LatencyMetrics, StructuredAnswer
from app.tools.catalog import (
    calculate_metric,
    compare_documents,
    generate_report_payload,
    infer_metric_from_question,
    periods_in_question,
    query_database,
)


def plan_question(question: str) -> dict[str, Any]:
    llm = get_llm_provider()
    raw = llm.complete_json("PLANNER\n" + load_prompt("planner.txt"), question)
    tools = raw.get("tools") if isinstance(raw.get("tools"), list) else ["search_documents"]
    return {
        "intent": raw.get("intent", "document_qa"),
        "tools": [str(t) for t in tools],
        "rationale": raw.get("rationale", ""),
        "needs_documents": bool(raw.get("needs_documents", True)),
        "needs_database": bool(raw.get("needs_database", False)),
    }


def run_orchestrator(db: Session, question: str, query_type: str, filters: dict[str, Any] | None, user_id: str | None) -> StructuredAnswer:
    t0 = time.perf_counter()
    plan = plan_question(question)
    tools_used: list[str] = []
    hits: list[Hit] = []
    db_facts: list[dict[str, Any]] = []
    extra_notes = f"Planner intent={plan.get('intent')} tools={plan.get('tools')}"

    hits, retrieval_ms, rerank_ms = retrieve_with_timing(db, question, filters)
    if hits:
        tools_used.append("search_documents")

    if "query_database" in plan["tools"] or plan.get("needs_database"):
        metric = infer_metric_from_question(question)
        periods = periods_in_question(question)
        year = 2024
        for period in periods:
            res = query_database(db, {"metric_name": metric, "year": year, "period": period, "department": "company"})
            tools_used.append("query_database")
            if res.ok and res.data:
                db_facts.extend(res.data)
        if "compare" in question.lower() or "calculate_metric" in plan["tools"]:
            values = [row["value"] for row in db_facts]
            if len(values) >= 2:
                calc = calculate_metric({"left_value": values[0], "right_value": values[-1], "operation": "pct_change"})
                tools_used.append("calculate_metric")
                if calc.ok:
                    db_facts.append({"comparison": calc.data})
                    extra_notes += f" pct_change={calc.data}"

    if "compare_documents" in plan["tools"]:
        periods = periods_in_question(question)
        left_q = f"{periods[0]} financial performance" if periods else "Q2 financial performance"
        right_q = f"{periods[-1]} financial performance" if len(periods) > 1 else "Q3 financial performance"
        cmp = compare_documents(db, left_q, right_q)
        tools_used.append("compare_documents")
        if cmp.ok:
            extra_notes += " document comparison executed."

    answer = generate_structured_answer(question, hits, db_facts, extra_notes)
    t_ver = time.perf_counter()
    verify_answer(answer, hits, db_facts)
    verification_ms = (time.perf_counter() - t_ver) * 1000

    answer.tools_used = list(dict.fromkeys(tools_used))
    total_ms = (time.perf_counter() - t0) * 1000
    answer.latency = LatencyMetrics(
        retrieval_ms=round(retrieval_ms, 2),
        rerank_ms=round(rerank_ms, 2),
        llm_ms=round(answer.latency.llm_ms, 2),
        verification_ms=round(verification_ms, 2),
        total_ms=round(total_ms, 2),
    )
    answer.retrieval = {
        "candidate_count": len(hits),
        "methods": list({h.retrieval_method for h in hits}),
        "filters": filters or {},
        "plan": plan,
    }

    if "generate_report" in plan["tools"] or query_type == "report":
        generate_report_payload(question, answer.answer, db_facts, hits)
        if "generate_report" not in answer.tools_used:
            answer.tools_used.append("generate_report")

    query = QueryRecord(user_id=user_id, question=question, query_type=query_type)
    db.add(query)
    db.flush()
    response = ResponseRecord(
        query_id=query.id,
        answer=answer.answer,
        confidence=answer.confidence,
        claims_json=json.dumps([c.model_dump() for c in answer.claims]),
        uncertainty_json=json.dumps(answer.uncertainty),
        tools_used_json=json.dumps(answer.tools_used),
        latency_json=json.dumps(answer.latency.model_dump()),
        verification_json=json.dumps(answer.verification),
    )
    db.add(response)
    db.flush()
    for i, ev in enumerate(hits_to_evidence(hits), start=1):
        db.add(
            Source(
                response_id=response.id,
                document_id=ev.chunk_id and hits[i - 1].document_id,
                chunk_id=ev.chunk_id,
                citation_index=i,
                page=ev.page,
                section=ev.section,
                snippet=ev.snippet or "",
                score=ev.score or 0,
                retrieval_method=ev.retrieval_method or "hybrid",
                document_name=ev.document,
            )
        )
    db.commit()
    answer.query_id = query.id
    answer.response_id = response.id
    return answer
