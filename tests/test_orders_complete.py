from datetime import date

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas import Company, OrderSummary


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return (1, "2026-08-29", "株式会社ABC", 12000)

    def fetchall(self):
        return [
            ("唐揚げ弁当", 2, 800, 1600),
            ("鮭弁当", 1, 850, 850),
        ]


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor()


def test_homepage_renders_company_and_bento_lists(monkeypatch):
    class HomePageConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return self

        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params

        def fetchall(self):
            if "FROM companies" in self.sql:
                return [(1, "株式会社ABC"), (2, "株式会社XYZ")]
            if "FROM bento" in self.sql:
                return [(1, "唐揚げ弁当", 800), (2, "鮭弁当", 850)]
            return []

    monkeypatch.setattr("app.main.get_connection",
                        lambda: HomePageConnection())

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "株式会社ABC" in response.text
    assert "株式会社XYZ" in response.text
    assert "唐揚げ弁当" in response.text
    assert "鮭弁当" in response.text


def test_order_complete_page_renders(monkeypatch):
    monkeypatch.setattr("app.main.get_connection", lambda: FakeConnection())

    client = TestClient(app)
    response = client.get("/orders/complete?order_id=1")

    assert response.status_code == 200
    assert "注文完了" in response.text
    assert "株式会社ABC" in response.text
    assert "12,000円" in response.text


class FakeOrderHistoryCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return [
            (1, "2026-08-29", "株式会社ABC", 12000),
            (2, "2026-08-30", "株式会社XYZ", 4500),
        ]


class FakeOrderHistoryConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeOrderHistoryCursor()


def test_order_history_page_renders(monkeypatch):
    monkeypatch.setattr("app.main.get_connection",
                        lambda: FakeOrderHistoryConnection())

    client = TestClient(app)
    response = client.get("/orders")

    assert response.status_code == 200
    assert "注文履歴" in response.text
    assert "株式会社ABC" in response.text
    assert "12,000円" in response.text


def test_order_history_page_handles_date_objects_from_db(monkeypatch):
    class DateObjectHistoryConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return self

        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return [
                (1, date(2026, 8, 29), "株式会社ABC", 12000),
                (2, date(2026, 8, 30), "株式会社XYZ", 4500),
            ]

    monkeypatch.setattr("app.main.get_connection", lambda: DateObjectHistoryConnection())

    client = TestClient(app)
    response = client.get("/orders")

    assert response.status_code == 200
    assert "2026-08-29" in response.text
    assert "株式会社ABC" in response.text


def test_immutable_models_are_frozen():
    company = Company(id=1, name="株式会社ABC")
    order = OrderSummary(
        id=1,
        order_date="2026-08-29",
        company_name="株式会社ABC",
        total_price=12000,
    )

    try:
        company.name = "変更後"
        raise AssertionError("Company should be immutable")
    except ValidationError:
        pass

    try:
        order.total_price = 9999
        raise AssertionError("OrderSummary should be immutable")
    except ValidationError:
        pass
