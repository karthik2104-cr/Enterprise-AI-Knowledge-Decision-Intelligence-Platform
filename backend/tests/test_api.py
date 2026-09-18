from io import BytesIO

from app.database.models import QueryRecord, Report
from app.database.session import SessionLocal


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_document_upload(client, auth_headers):
    content = b"# Demo Policy\n\nEmployees may request remote work twice per week with manager approval."
    files = {"file": ("remote_work.txt", BytesIO(content), "text/plain")}
    res = client.post("/api/documents", files=files, data={"department": "people", "doc_type": "policy", "year": "2024"}, headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "indexed"
    assert body["chunk_count"] >= 1
    listed = client.get("/api/documents", headers=auth_headers)
    assert listed.status_code == 200
    assert any(d["id"] == body["id"] for d in listed.json())


def test_search_endpoint(client, auth_headers):
    res = client.post("/api/search", json={"query": "leave policy"}, headers=auth_headers)
    assert res.status_code == 200
    hits = res.json()
    assert hits
    assert "snippet" in hits[0]
    assert "score_explanation" in hits[0]


def test_ask_endpoint(client, auth_headers):
    res = client.post("/api/ask", json={"question": "What is the company's leave policy?"}, headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["answer"]
    assert "confidence" in data
    assert "tools_used" in data


def test_report_endpoint(client, auth_headers):
    res = client.post("/api/report", json={"question": "Generate a report about Q3 performance."}, headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert "sections" in data["content"]
    assert "executive_summary" in data["content"]["sections"]
    db = SessionLocal()
    try:
        assert db.query(Report).count() >= 1
        assert db.query(QueryRecord).count() >= 1
    finally:
        db.close()


def test_evaluation_endpoint(client, auth_headers):
    res = client.post("/api/evaluation/run", headers=auth_headers)
    assert res.status_code == 200, res.text
    metrics = res.json()["metrics"]
    assert "precision_at_5" in metrics
    listed = client.get("/api/evaluation", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()
    results = client.get("/api/evaluation/results", headers=auth_headers)
    assert results.status_code == 200
    assert results.json()


def test_query_history(client, auth_headers):
    client.post("/api/ask", json={"question": "What was Q3 revenue?"}, headers=auth_headers)
    hist = client.get("/api/history", headers=auth_headers)
    assert hist.status_code == 200
    items = hist.json()
    assert items
    detail = client.get(f"/api/history/{items[0]['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["question"]
