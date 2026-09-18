from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.models import BusinessMetric, User
from app.documents.ingestion import ingest_text_document

SAMPLE_DIR = Path(__file__).resolve().parents[3] / "sample_data" / "documents"

METRICS = [
    (2024, "Q1", "revenue", "company", 11_200_000, "usd", "Demo synthetic metric"),
    (2024, "Q2", "revenue", "company", 12_400_000, "usd", "Demo synthetic metric"),
    (2024, "Q3", "revenue", "company", 13_888_000, "usd", "Demo synthetic metric"),
    (2024, "Q1", "expenses", "company", 8_100_000, "usd", None),
    (2024, "Q2", "expenses", "company", 8_650_000, "usd", None),
    (2024, "Q3", "expenses", "company", 9_210_000, "usd", None),
    (2024, "Q1", "operating_income", "company", 3_100_000, "usd", None),
    (2024, "Q2", "operating_income", "company", 3_750_000, "usd", None),
    (2024, "Q3", "operating_income", "company", 4_678_000, "usd", None),
    (2024, "Q1", "headcount", "company", 412, "count", None),
    (2024, "Q2", "headcount", "company", 428, "count", None),
    (2024, "Q3", "headcount", "company", 441, "count", None),
    (2024, "Q2", "gross_margin_pct", "company", 58.2, "percent", None),
    (2024, "Q3", "gross_margin_pct", "company", 61.4, "percent", None),
    (2024, "Q2", "customer_nps", "company", 41, "score", None),
    (2024, "Q3", "customer_nps", "company", 47, "score", None),
    (2024, "Q2", "attrition_pct", "people", 11.5, "percent", None),
    (2024, "Q3", "attrition_pct", "people", 9.8, "percent", None),
    (2024, "Q2", "support_tickets", "operations", 1840, "count", None),
    (2024, "Q3", "support_tickets", "operations", 1612, "count", None),
    (2024, "Q3", "revenue", "sales", 9_400_000, "usd", None),
    (2024, "Q3", "revenue", "engineering", 0, "usd", "Cost center"),
]


DOC_META = {
    "employee_handbook.md": ("Employee Handbook", "people", "policy", 2024),
    "leave_policy.md": ("Leave Policy", "people", "policy", 2024),
    "benefits_guide.md": ("Benefits Guide", "people", "policy", 2024),
    "q2_financial_report.md": ("Q2 Financial Report", "finance", "financial_report", 2024),
    "q3_financial_report.md": ("Q3 Financial Report", "finance", "financial_report", 2024),
    "compliance_guidelines.md": ("Compliance Guidelines", "legal", "compliance", 2024),
    "it_security_policy.md": ("IT Security Policy", "it", "policy", 2024),
    "procurement_policy.md": ("Procurement Policy", "operations", "policy", 2024),
}


def seed_if_empty(db: Session) -> None:
    settings = get_settings()
    user = db.query(User).filter(User.email == settings.demo_email).first()
    if not user:
        db.add(
            User(
                email=settings.demo_email,
                hashed_password=hash_password(settings.demo_password),
                full_name=settings.demo_name,
                role="analyst",
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    if db.query(BusinessMetric).count() == 0:
        for year, period, name, dept, value, unit, notes in METRICS:
            db.add(
                BusinessMetric(
                    year=year,
                    period=period,
                    metric_name=name,
                    department=dept,
                    value=value,
                    unit=unit,
                    notes=notes,
                )
            )
        db.commit()

    if SAMPLE_DIR.exists():
        for path in sorted(SAMPLE_DIR.glob("*.md")):
            meta = DOC_META.get(path.name)
            if not meta:
                continue
            title, dept, doc_type, year = meta
            ingest_text_document(db, title, path.read_text(encoding="utf-8"), path.name, dept, doc_type, year)
