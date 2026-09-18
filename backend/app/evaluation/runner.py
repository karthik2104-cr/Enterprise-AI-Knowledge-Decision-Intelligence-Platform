from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_orchestrator
from app.database.models import EvaluationResult, EvaluationRun
from app.retrieval.service import retrieve

DATASET_PATH = Path(__file__).resolve().parents[3] / "evaluation" / "dataset" / "golden_set.json"


def load_dataset() -> list[dict[str, Any]]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top = retrieved[:k]
    if not top:
        return 0.0
    return len([d for d in top if _match(d, relevant)]) / len(top)


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    return len([r for r in relevant if _match(r, top)]) / len(relevant)


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    for i, doc in enumerate(retrieved, start=1):
        if _match(doc, relevant):
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k], start=1):
        rel = 1.0 if _match(doc, relevant) else 0.0
        dcg += rel / math.log2(i + 1)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(k, len(relevant)) + 1))
    return dcg / ideal if ideal else 0.0


def _match(name: str, options: list[str]) -> bool:
    n = name.lower()
    return any(opt.lower() in n or n in opt.lower() for opt in options)


def token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def run_evaluation(db: Session, name: str = "golden-set") -> EvaluationRun:
    dataset = load_dataset()
    run = EvaluationRun(name=name, status="running", metrics_json="{}")
    db.add(run)
    db.commit()
    db.refresh(run)

    per: list[dict[str, Any]] = []
    for item in dataset:
        question = item["question"]
        expected_docs = item.get("expected_evidence", [])
        expected_answer = item.get("expected_answer", "")
        hits = retrieve(db, question)
        retrieved_names = [h.document_name for h in hits]
        answer = run_orchestrator(db, question, "evaluation", {}, None)
        actual = answer.answer
        p_at_5 = precision_at_k(retrieved_names, expected_docs, 5)
        r_at_5 = recall_at_k(retrieved_names, expected_docs, 5)
        mrr_v = mrr(retrieved_names, expected_docs)
        ndcg = ndcg_at_k(retrieved_names, expected_docs, 5)
        relevance = token_overlap(actual, expected_answer)
        correctness = 1.0 if relevance >= 0.18 or any(k.lower() in actual.lower() for k in item.get("must_include", [])) else 0.0
        grounded = float(answer.verification.get("groundedness", 0))
        citation_ok = 1.0 if (not expected_docs or r_at_5 > 0) and answer.sources else 0.0
        halluc = 1.0 if answer.verification.get("status") == "uncertain" and "unsupported" in " ".join(answer.uncertainty).lower() else 0.0
        if actual.lower().startswith("i couldn't find") and expected_answer:
            halluc = 0.0
            correctness = 0.0
        passed = int(correctness >= 1.0 and grounded >= 0.4)
        metrics = {
            "precision_at_5": p_at_5,
            "recall_at_5": r_at_5,
            "mrr": mrr_v,
            "ndcg_at_5": ndcg,
            "answer_correctness": correctness,
            "answer_relevance": round(relevance, 3),
            "groundedness": grounded,
            "citation_correctness": citation_ok,
            "unsupported_claim_rate": halluc,
            "latency_ms": answer.latency.total_ms,
        }
        db.add(
            EvaluationResult(
                run_id=run.id,
                question=question,
                expected_answer=expected_answer,
                actual_answer=actual,
                expected_evidence=json.dumps(expected_docs),
                retrieved_documents=json.dumps(list(dict.fromkeys(retrieved_names))),
                metrics_json=json.dumps(metrics),
                passed=passed,
            )
        )
        per.append(metrics)

    def avg(key: str) -> float:
        vals = [p[key] for p in per]
        return round(sum(vals) / max(len(vals), 1), 4)

    summary = {
        "questions": len(per),
        "precision_at_5": avg("precision_at_5"),
        "recall_at_5": avg("recall_at_5"),
        "mrr": avg("mrr"),
        "ndcg_at_5": avg("ndcg_at_5"),
        "answer_correctness": avg("answer_correctness"),
        "answer_relevance": avg("answer_relevance"),
        "groundedness": avg("groundedness"),
        "citation_correctness": avg("citation_correctness"),
        "unsupported_claim_rate": avg("unsupported_claim_rate"),
        "avg_latency_ms": avg("latency_ms"),
        "pass_rate": round(sum(1 for p in per if p["answer_correctness"] >= 1) / max(len(per), 1), 4),
    }
    run.metrics_json = json.dumps(summary)
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    results_dir = Path(__file__).resolve().parents[3] / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{run.id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return run
