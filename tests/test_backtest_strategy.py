import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_backtest_stop_take():
    client = TestClient(app)
    payload = {
        "ticker": "AAPL",
        "window": 10,
        "interval": "1h",
        "start_date": None,
        "end_date": None,
        "step": 1,
        "include_news": False
    }
    resp = client.post("/api/backtest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "trades" in data
    assert data["summary"].get("trades_count") is not None
