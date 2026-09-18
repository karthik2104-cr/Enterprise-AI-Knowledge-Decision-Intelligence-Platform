from app.agents.verifier import verify_answer
from app.database.session import SessionLocal
from app.rag.pipeline import INSUFFICIENT, construct_context, generate_structured_answer
from app.retrieval.service import retrieve
from app.schemas.common import StructuredAnswer


def test_context_construction():
    db = SessionLocal()
    try:
        hits = retrieve(db, "leave policy")
        ctx = construct_context(hits)
        assert "Leave" in ctx or "leave" in ctx.lower()
        assert hits[0].chunk_id
    finally:
        db.close()


def test_source_tracking():
    db = SessionLocal()
    try:
        hits = retrieve(db, "reimbursement policy")
        answer = generate_structured_answer("What is the reimbursement policy?", hits, [])
        assert answer.sources
        assert answer.sources[0].chunk_id
        assert answer.sources[0].document
    finally:
        db.close()


def test_empty_retrieval():
    answer = generate_structured_answer("What is the secret nuclear launch code?", [], [])
    assert INSUFFICIENT.split()[0] in answer.answer
    assert answer.confidence < 0.3


def test_grounded_response():
    db = SessionLocal()
    try:
        hits = retrieve(db, "20 days of paid annual leave")
        answer = generate_structured_answer("What is the company's leave policy?", hits, [])
        assert "leave" in answer.answer.lower() or "days" in answer.answer.lower()
        assert answer.sources
    finally:
        db.close()


def test_structured_output():
    parsed = StructuredAnswer(answer="ok", confidence=0.5)
    assert parsed.confidence == 0.5


def test_invalid_llm_response():
    from app.providers.llm import safe_parse_json

    assert safe_parse_json("not json") == {}
    assert safe_parse_json('{"answer":"x"}')["answer"] == "x"


def test_verifier():
    db = SessionLocal()
    try:
        hits = retrieve(db, "leave")
        answer = generate_structured_answer("What is the leave policy?", hits, [])
        result = verify_answer(answer, hits)
        assert result["status"] in {"pass", "uncertain", "insufficient_evidence"}
        assert result["guarantees_truth"] is False
    finally:
        db.close()
