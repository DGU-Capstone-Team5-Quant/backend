import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_backtest_point_stub():
    client = TestClient(app)
    payload = {
        "ticker": "AAPL",
        "window": 10,
        "interval": "1h",
        "target_datetime": None
    }
    resp = client.post("/api/point", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert data["backtest_id"]
