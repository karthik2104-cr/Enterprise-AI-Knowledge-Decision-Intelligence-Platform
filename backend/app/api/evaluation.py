import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.models import EvaluationResult, EvaluationRun, User
from app.database.session import get_db
from app.evaluation.runner import run_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("")
def list_runs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.started_at.desc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "status": r.status,
            "metrics": json.loads(r.metrics_json or "{}"),
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.post("/run")
def start_run(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    run = run_evaluation(db)
    return {"id": run.id, "status": run.status, "metrics": json.loads(run.metrics_json or "{}")}


@router.get("/results")
def results(run_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    query = db.query(EvaluationResult)
    if run_id:
        query = query.filter(EvaluationResult.run_id == run_id)
    else:
        latest = db.query(EvaluationRun).order_by(EvaluationRun.started_at.desc()).first()
        if not latest:
            return []
        query = query.filter(EvaluationResult.run_id == latest.id)
    rows = query.all()
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "question": r.question,
            "expected_answer": r.expected_answer,
            "actual_answer": r.actual_answer,
            "expected_evidence": json.loads(r.expected_evidence or "[]"),
            "retrieved_documents": json.loads(r.retrieved_documents or "[]"),
            "metrics": json.loads(r.metrics_json or "{}"),
            "passed": bool(r.passed),
        }
        for r in rows
    ]


@router.get("/results/{result_id}")
def one_result(result_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.query(EvaluationResult).filter(EvaluationResult.id == result_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    return row.id
