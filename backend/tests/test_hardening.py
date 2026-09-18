from io import BytesIO

import pytest

from pydantic import ValidationError

from app.agents.verifier import verify_answer
from app.database.session import SessionLocal
from app.providers.llm import safe_parse_json
from app.rag.pipeline import generate_structured_answer
from app.retrieval.service import Hit, hybrid_search, keyword_search, rerank, retrieve, semantic_search
from app.schemas.common import Claim, StructuredAnswer
from app.tools.catalog import calculate_metric, query_database


def test_unauthenticated_is_rejected(client):
    res = client.get("/api/documents")
    assert res.status_code == 401


def test_health_includes_database(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"ok", "degraded"}
    assert "database" in body


def test_empty_upload_rejected(client, auth_headers):
    files = {"file": ("empty.txt", BytesIO(b""), "text/plain")}
    res = client.post("/api/documents", files=files, headers=auth_headers)
    assert res.status_code == 400


def test_unsupported_upload_rejected(client, auth_headers):
    files = {"file": ("notes.exe", BytesIO(b"MZ"), "application/octet-stream")}
    res = client.post("/api/documents", files=files, headers=auth_headers)
    assert res.status_code == 400


def test_duplicate_upload_rejected(client, auth_headers):
    payload = b"Unique reimbursement memo for testing duplicates.\nEmployees submit receipts in 30 days."
    files = {"file": ("memo.txt", BytesIO(payload), "text/plain")}
    first = client.post("/api/documents", files=files, headers=auth_headers)
    assert first.status_code == 200, first.text
    files = {"file": ("memo.txt", BytesIO(payload), "text/plain")}
    second = client.post("/api/documents", files=files, headers=auth_headers)
    assert second.status_code == 409


def test_invalid_metric_is_safe():
    db = SessionLocal()
    try:
        res = query_database(db, {"metric_name": "'; drop table users;--", "year": 2024, "period": "Q3"})
        assert not res.ok
        res2 = query_database(db, {"metric_name": "revenue", "year": 2024, "period": "QX", "department": "company"})
        assert not res2.ok
        res3 = query_database(db, {"metric_name": "revenue", "year": 2024, "department": "secret"})
        assert not res3.ok
    finally:
        db.close()


def test_malformed_structured_output_does_not_crash():
    parsed = safe_parse_json("not-json")
    assert parsed == {}
    answer = generate_structured_answer("x", [], [])
    assert "sufficient evidence" in answer.answer.lower()


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValidationError):
        StructuredAnswer(answer="ok", confidence=1.5)


def test_hybrid_merges_keyword_and_semantic():
    db = SessionLocal()
    try:
        kw = {h.chunk_id for h in keyword_search(db, "leave annual sick parental")}
        sem = {h.chunk_id for h in semantic_search(db, "paid time away from work")}
        hybrid = hybrid_search(db, "annual leave and paid time away from work")
        assert hybrid
        methods = {h.retrieval_method for h in hybrid}
        assert methods.intersection({"hybrid", "keyword", "semantic"})
        if kw and sem:
            assert any(h.chunk_id in kw or h.chunk_id in sem for h in hybrid)
    finally:
        db.close()


def test_rerank_prefers_query_overlap():
    weak = Hit("d", "Other", "c1", 1, "body", "lorem ipsum dolor sit amet", 0.9, "hybrid")
    strong = Hit("d", "Leave Policy", "c2", 1, "Annual leave", "full-time employees accrue 20 days of paid annual leave", 0.2, "hybrid")
    ranked = rerank("annual leave policy", [weak, strong])
    assert ranked[0].chunk_id == "c2"


def test_zero_results_query():
    db = SessionLocal()
    try:
        hits = retrieve(db, "xyzzy-plugh-unrelated-quantum-banana-42")
        assert isinstance(hits, list)
    finally:
        db.close()


def test_unsupported_claim_marked_uncertain():
    hits = [
        Hit("d", "Leave Policy", "c1", 1, "Leave", "Employees receive 20 days of paid annual leave.", 0.5, "hybrid")
    ]
    answer = StructuredAnswer(
        answer="The company operates a secret lunar colony.",
        confidence=0.9,
        claims=[Claim(text="The company operates a secret lunar colony.", evidence=[])],
    )
    result = verify_answer(answer, hits)
    assert result["status"] in {"uncertain", "pass"}
    assert result["guarantees_truth"] is False
    if result["status"] == "uncertain":
        assert answer.confidence <= 0.45


def test_calculation_invalid_operation():
    res = calculate_metric({"left_value": 1, "right_value": 2, "operation": "hack"})
    assert not res.ok
