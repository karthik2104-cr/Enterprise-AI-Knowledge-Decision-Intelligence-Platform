import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_orchestrator
from app.auth.deps import get_current_user
from app.database.models import Report, User
from app.database.session import get_db
from app.retrieval.service import Hit
from app.schemas.common import AskRequest, ReportOut, ReportRequest, StructuredAnswer
from app.tools.catalog import calculate_metric, generate_report_payload, periods_in_question, query_database

router = APIRouter(prefix="/api", tags=["intelligence"])


@router.post("/ask", response_model=StructuredAnswer)
def ask(payload: AskRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return run_orchestrator(db, payload.question, "ask", payload.filters, user.id)


@router.post("/analyze", response_model=StructuredAnswer)
def analyze(payload: AskRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return run_orchestrator(db, payload.question, "analyze", payload.filters, user.id)


@router.post("/report", response_model=ReportOut)
def create_report(payload: ReportRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    answer = run_orchestrator(db, payload.question, "report", {}, user.id)
    periods = periods_in_question(payload.question)
    if len(periods) == 1 and periods[0] in {"Q2", "Q3", "Q4"}:
        prior = {"Q2": "Q1", "Q3": "Q2", "Q4": "Q3"}[periods[0]]
        periods = [prior, periods[0]]
    facts: list[dict] = []
    for metric in ("revenue", "expenses", "operating_income", "headcount"):
        for period in periods:
            res = query_database(db, {"metric_name": metric, "year": 2024, "period": period, "department": "company"})
            if res.ok and res.data:
                facts.extend(res.data)
    revenue_vals = [row["value"] for row in facts if row.get("metric") == "revenue"]
    if len(revenue_vals) >= 2:
        calc = calculate_metric(
            {"left_value": revenue_vals[0], "right_value": revenue_vals[-1], "operation": "pct_change"}
        )
        if calc.ok:
            facts.append({"comparison": calc.data})
    hits = [
        Hit(
            document_id=s.chunk_id or "",
            document_name=s.document,
            chunk_id=s.chunk_id or "",
            page=s.page,
            section=s.section,
            content=s.snippet or "",
            score=s.score or 0,
            retrieval_method=s.retrieval_method or "hybrid",
        )
        for s in answer.sources
    ]
    tool = generate_report_payload(payload.question, answer.answer, facts, hits)
    title = payload.title or payload.question[:80]
    report = Report(
        user_id=user.id,
        title=title,
        question=payload.question,
        status="completed",
        content_json=json.dumps({**(tool.data or {}), "answer": answer.model_dump()}),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_out(report)


@router.get("/reports", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Report).order_by(Report.created_at.desc()).all()
    return [_report_out(r) for r in rows]


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_out(report)


def _report_out(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        title=report.title,
        question=report.question,
        status=report.status,
        content=json.loads(report.content_json or "{}"),
        created_at=report.created_at.isoformat() if report.created_at else None,
    )
