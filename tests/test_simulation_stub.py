import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_run_simulation_stub():
    client = TestClient(app)
    payload = {
        "ticker": "AAPL",
        "window": 10,
        "mode": "intraday",
        "interval": "1h",
        "news": False
    }
    resp = client.post("/api/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "summary" in data
