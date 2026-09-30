import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'test.db'}"

import importlib.util

spec = importlib.util.spec_from_file_location("alerts_svc", ROOT / "services" / "alerts" / "app" / "main.py")
alerts_mod = importlib.util.module_from_spec(spec)
sys.modules["alerts_svc"] = alerts_mod
spec.loader.exec_module(alerts_mod)

app = alerts_mod.app
init_db = alerts_mod.init_db
SessionLocal = alerts_mod.SessionLocal
seed_initial_alerts = alerts_mod.seed_initial_alerts

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_alerts_db():
    init_db()
    with SessionLocal() as db:
        seed_initial_alerts(db)
    yield


def test_alerts_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "alerts", "database": "connected"}


def test_create_alert():
    payload = {
        "type": "accident",
        "severity": "critical",
        "road_id": "R001",
        "message": "Expressway: Multi-vehicle collision at km 14; right lane blocked.",
    }
    res = client.post("/api/v1/alerts", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "alert_id" in data
    assert data["type"] == "accident"
    assert data["severity"] == "critical"
    assert data["road_id"] == "R001"


def test_get_my_alerts():
    res = client.get("/api/v1/alerts/my")
    assert res.status_code == 200
    alerts = res.json()
    assert isinstance(alerts, list)
    assert len(alerts) > 0
    first = alerts[0]
    assert "alert_id" in first
    assert "type" in first
    assert "severity" in first
    assert "message" in first
    assert "read" in first


def test_get_my_alerts_public_scope():
    res = client.get("/api/v1/alerts/my?role=public")
    assert res.status_code == 200
    alerts = res.json()
    assert isinstance(alerts, list)
    # Public scope should only see high/critical severity or incident types
    for a in alerts:
        assert a["severity"] in ("high", "critical", "medium") or a["type"] in ("accident", "closure", "hazard")


def test_mark_alert_read():
    # First get an active alert
    active = client.get("/api/v1/alerts/active").json()
    assert len(active) > 0
    target_id = active[0]["alert_id"]

    res = client.post(f"/api/v1/alerts/{target_id}/read")
    assert res.status_code == 200
    assert res.json() == {"alert_id": target_id, "read": True}


def test_get_active_alerts():
    res = client.get("/api/v1/alerts/active")
    assert res.status_code == 200
    active = res.json()
    assert isinstance(active, list)
    for a in active:
        assert a["read"] is False
