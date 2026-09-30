import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'trafficvision.db'}"

import importlib.util

spec = importlib.util.spec_from_file_location("analytics_svc", ROOT / "services" / "analytics" / "app" / "main.py")
analytics_mod = importlib.util.module_from_spec(spec)
sys.modules["analytics_svc"] = analytics_mod
spec.loader.exec_module(analytics_mod)

app = analytics_mod.app
client = TestClient(app)


def test_analytics_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "analytics"}


def test_analytics_trends_day():
    res = client.get("/api/v1/analytics/trends?road_id=R001&range=day")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R001"
    assert data["range"] == "day"
    assert "points" in data
    assert isinstance(data["points"], list)
    assert len(data["points"]) > 0
    p = data["points"][0]
    assert "period" in p
    assert "avg_congestion" in p
    assert "avg_speed" in p


def test_analytics_trends_week():
    res = client.get("/api/v1/analytics/trends?road_id=R001&range=week")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R001"
    assert data["range"] == "week"
    assert "points" in data
    assert isinstance(data["points"], list)


def test_analytics_heatmap():
    res = client.get("/api/v1/analytics/heatmap?range=day")
    assert res.status_code == 200
    data = res.json()
    assert "roads" in data
    assert "time_buckets" in data
    assert "values" in data
    assert len(data["roads"]) > 0
    assert len(data["time_buckets"]) == 24
    assert len(data["values"]) == len(data["roads"])
    assert len(data["values"][0]) == 24


def test_analytics_reports_csv():
    res = client.get("/api/v1/analytics/reports?range=week&format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "road_id" in res.text


def test_analytics_reports_json():
    res = client.get("/api/v1/analytics/reports?range=week&format=json")
    assert res.status_code == 200
    data = res.json()
    assert "record_count" in data
    assert "data" in data
    assert isinstance(data["data"], list)
