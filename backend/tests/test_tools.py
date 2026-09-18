from app.database.session import SessionLocal
from app.tools.catalog import calculate_metric, compare_documents, query_database


def test_database_tool():
    db = SessionLocal()
    try:
        res = query_database(db, {"metric_name": "revenue", "year": 2024, "period": "Q3"})
        assert res.ok
        assert res.data
        assert res.data[0]["value"] == 13888000
        bad = query_database(db, {"metric_name": "drop_table", "year": 2024})
        assert not bad.ok
    finally:
        db.close()


def test_calculation_tool():
    res = calculate_metric({"left_value": 12400000, "right_value": 13888000, "operation": "pct_change"})
    assert res.ok
    assert 11 < res.data["value"] < 13
    zero = calculate_metric({"left_value": 0, "right_value": 1, "operation": "pct_change"})
    assert not zero.ok


def test_document_comparison():
    db = SessionLocal()
    try:
        res = compare_documents(db, "Q2 revenue", "Q3 revenue")
        assert res.ok
        assert res.data["left"] or res.data["right"]
    finally:
        db.close()
