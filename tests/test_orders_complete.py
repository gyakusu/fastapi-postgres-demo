from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import db
from app.main import app, format_yen, parse_quantities
from app.schemas import Company, OrderSummary


class FakeCursor:
    def __init__(self, *, fetchone_result=None, fetchall_results=()):
        self.fetchone_result = fetchone_result
        self.fetchall_results = iter(fetchall_results)
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def executemany(self, sql, params_seq):
        self.sql = sql
        self.params = list(params_seq)

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return next(self.fetchall_results, [])


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor

    def transaction(self):
        return FakeTransaction()


def test_format_yen():
    assert format_yen(12000) == "12,000円"


def test_homepage_renders_company_and_bento_lists(monkeypatch):
    class HomeCursor(FakeCursor):
        def fetchall(self):
            if "FROM companies" in self.sql:
                return [(1, "株式会社ABC"), (2, "株式会社XYZ")]
            if "FROM bento b" in self.sql:
                return [
                    ("唐揚げ弁当", "小麦"),
                    ("唐揚げ弁当", "卵"),
                    ("鮭弁当", None),
                ]
            if "FROM bento" in self.sql:
                return [(1, "唐揚げ弁当", 800), (2, "鮭弁当", 850)]
            return []

    monkeypatch.setattr(
        db,
        "get_connection",
        lambda: FakeConnection(HomeCursor()),
    )

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "株式会社ABC" in response.text
    assert "株式会社XYZ" in response.text
    assert "唐揚げ弁当" in response.text
    assert "鮭弁当" in response.text
    assert "小麦, 卵" in response.text


def test_order_complete_page_renders(monkeypatch):
    cursor = FakeCursor(
        fetchone_result=(1, "2026-08-29", "株式会社ABC", 12000),
        fetchall_results=[[
            ("唐揚げ弁当", 2, 800, 1600),
            ("鮭弁当", 1, 850, 850),
        ]],
    )
    monkeypatch.setattr(
        db,
        "get_connection",
        lambda: FakeConnection(cursor),
    )

    response = TestClient(app).get("/orders/complete?order_id=1")

    assert response.status_code == 200
    assert "注文完了" in response.text
    assert "株式会社ABC" in response.text
    assert "12,000円" in response.text


def test_order_history_page_renders(monkeypatch):
    cursor = FakeCursor(
        fetchall_results=[[
            (1, "2026-08-29", "株式会社ABC", 12000),
            (2, "2026-08-30", "株式会社XYZ", 4500),
        ]],
    )
    monkeypatch.setattr(
        db,
        "get_connection",
        lambda: FakeConnection(cursor),
    )

    response = TestClient(app).get("/orders")

    assert response.status_code == 200
    assert "注文履歴" in response.text
    assert "株式会社ABC" in response.text
    assert "12,000円" in response.text


def test_order_history_page_handles_date_objects_from_db(monkeypatch):
    cursor = FakeCursor(
        fetchall_results=[[
            (1, date(2026, 8, 29), "株式会社ABC", 12000),
            (2, date(2026, 8, 30), "株式会社XYZ", 4500),
        ]],
    )
    monkeypatch.setattr(
        db,
        "get_connection",
        lambda: FakeConnection(cursor),
    )

    response = TestClient(app).get("/orders")

    assert response.status_code == 200
    assert "2026-08-29" in response.text
    assert "株式会社ABC" in response.text


def test_order_complete_returns_404_for_unknown_order(monkeypatch):
    cursor = FakeCursor(fetchone_result=None)
    monkeypatch.setattr(
        db,
        "get_connection",
        lambda: FakeConnection(cursor),
    )

    response = TestClient(app).get("/orders/complete?order_id=999")

    assert response.status_code == 404


def test_parse_quantities_ignores_invalid_and_zero_values():
    form = {
        "quantity_1": "2",
        "quantity_2": "0",
        "quantity_3": "invalid",
        "other_field": "100",
    }

    quantities = parse_quantities(form)

    assert len(quantities) == 1
    assert quantities[0].bento_id == 1
    assert quantities[0].quantity == 2


def test_parse_quantities_requires_positive_quantity():
    with pytest.raises(HTTPException, match="At least one bento quantity"):
        parse_quantities({"quantity_1": "0"})


def test_immutable_models_are_frozen():
    company = Company(id=1, name="株式会社ABC")
    order = OrderSummary(
        id=1,
        order_date="2026-08-29",
        company_name="株式会社ABC",
        total_price=12000,
    )

    with pytest.raises(ValidationError):
        company.name = "変更後"

    with pytest.raises(ValidationError):
        order.total_price = 9999
