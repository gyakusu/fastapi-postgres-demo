from fastapi.testclient import TestClient

from app.main import app


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
