from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.models import BusinessMetric
from app.retrieval.service import Hit, retrieve


ALLOWED_METRICS = {
    "revenue",
    "expenses",
    "operating_income",
    "headcount",
    "customer_nps",
    "gross_margin_pct",
    "attrition_pct",
    "support_tickets",
}

ALLOWED_PERIODS = {"Q1", "Q2", "Q3", "Q4", "FY"}
ALLOWED_DEPARTMENTS = {"company", "engineering", "sales", "operations", "people", "finance"}


class ToolResult(BaseModel):
    tool: str
    ok: bool
    data: Any = None
    error: str | None = None


class MetricQuery(BaseModel):
    metric_name: str
    year: int = 2024
    period: str | None = None
    department: str = "company"


class CalcRequest(BaseModel):
    left_value: float
    right_value: float
    operation: str = Field(pattern="^(delta|pct_change|ratio|sum)$")


def search_documents(db: Session, query: str, filters: dict[str, Any] | None = None) -> ToolResult:
    try:
        hits = retrieve(db, query, filters)
        return ToolResult(tool="search_documents", ok=True, data=[_hit_dict(h) for h in hits])
    except Exception as exc:
        return ToolResult(tool="search_documents", ok=False, error=str(exc))


def query_database(db: Session, payload: dict[str, Any]) -> ToolResult:
    try:
        args = MetricQuery.model_validate(payload)
        name = args.metric_name.lower().replace(" ", "_")
        if name not in ALLOWED_METRICS:
            return ToolResult(tool="query_database", ok=False, error=f"Unknown metric '{name}'. Allowed: {sorted(ALLOWED_METRICS)}")
        department = args.department.lower()
        if department not in ALLOWED_DEPARTMENTS:
            return ToolResult(tool="query_database", ok=False, error="Department is not in the approved catalog.")
        q = db.query(BusinessMetric).filter(
            BusinessMetric.metric_name == name,
            BusinessMetric.year == args.year,
            BusinessMetric.department == department,
        )
        if args.period:
            period = args.period.upper()
            if period not in ALLOWED_PERIODS:
                return ToolResult(tool="query_database", ok=False, error="Period must be Q1-Q4 or FY.")
            q = q.filter(BusinessMetric.period == period)
        rows = q.order_by(BusinessMetric.period.asc()).all()
        data = [
            {"year": r.year, "period": r.period, "metric": r.metric_name, "department": r.department, "value": r.value, "unit": r.unit, "notes": r.notes}
            for r in rows
        ]
        return ToolResult(tool="query_database", ok=True, data=data)
    except Exception as exc:
        return ToolResult(tool="query_database", ok=False, error=str(exc))


def calculate_metric(payload: dict[str, Any]) -> ToolResult:
    try:
        args = CalcRequest.model_validate(payload)
        a, b = args.left_value, args.right_value
        if args.operation == "delta":
            value = b - a
        elif args.operation == "pct_change":
            if a == 0:
                return ToolResult(tool="calculate_metric", ok=False, error="Cannot compute percent change from zero.")
            value = (b - a) / a * 100
        elif args.operation == "ratio":
            if b == 0:
                return ToolResult(tool="calculate_metric", ok=False, error="Cannot divide by zero.")
            value = a / b
        else:
            value = a + b
        return ToolResult(tool="calculate_metric", ok=True, data={"operation": args.operation, "left": a, "right": b, "value": round(value, 4)})
    except Exception as exc:
        return ToolResult(tool="calculate_metric", ok=False, error=str(exc))


def compare_documents(db: Session, left_query: str, right_query: str) -> ToolResult:
    try:
        left = retrieve(db, left_query)
        right = retrieve(db, right_query)
        return ToolResult(
            tool="compare_documents",
            ok=True,
            data={"left": [_hit_dict(h) for h in left[:4]], "right": [_hit_dict(h) for h in right[:4]]},
        )
    except Exception as exc:
        return ToolResult(tool="compare_documents", ok=False, error=str(exc))


def generate_report_payload(question: str, answer: str, metrics: list[dict], hits: list[Hit]) -> ToolResult:
    changes = []
    for item in metrics:
        if not isinstance(item, dict):
            continue
        if "comparison" in item and isinstance(item["comparison"], dict):
            changes.append(item["comparison"])
        elif item.get("operation") in {"pct_change", "delta"}:
            changes.append(item)
    sections = {
        "executive_summary": answer[:900],
        "key_metrics": [m for m in metrics if isinstance(m, dict) and m.get("metric")],
        "major_changes": changes,
        "analysis": answer,
        "supporting_evidence": [_hit_dict(h) for h in hits[:6]],
        "sources": list(dict.fromkeys(h.document_name for h in hits)),
    }
    return ToolResult(tool="generate_report", ok=True, data={"title": question[:120], "question": question, "sections": sections})


def _hit_dict(h: Hit) -> dict[str, Any]:
    return {
        "document": h.document_name,
        "document_id": h.document_id,
        "page": h.page,
        "section": h.section,
        "chunk_id": h.chunk_id,
        "snippet": h.snippet(),
        "score": h.score,
        "retrieval_method": h.retrieval_method,
    }


def infer_metric_from_question(question: str) -> str:
    q = question.lower()
    mapping = [
        ("nps", "customer_nps"),
        ("margin", "gross_margin_pct"),
        ("attrition", "attrition_pct"),
        ("headcount", "headcount"),
        ("employee", "headcount"),
        ("ticket", "support_tickets"),
        ("expense", "expenses"),
        ("operating", "operating_income"),
        ("revenue", "revenue"),
    ]
    for needle, metric in mapping:
        if needle in q:
            return metric
    return "revenue"


def periods_in_question(question: str) -> list[str]:
    order = ["Q1", "Q2", "Q3", "Q4", "FY"]
    found = [p for p in order if p.lower() in question.lower()]
    return found or ["Q3"]
