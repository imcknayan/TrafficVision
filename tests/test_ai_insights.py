import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

import importlib.util

spec = importlib.util.spec_from_file_location("ai_insights_main", ROOT / "services" / "ai-engine" / "app" / "main.py")
ai_mod = importlib.util.module_from_spec(spec)
sys.modules["ai_insights_main"] = ai_mod
spec.loader.exec_module(ai_mod)

app = ai_mod.app
client = TestClient(app)


def test_ai_anomalies_detection():
    res = client.get("/api/v1/ai/anomalies")
    assert res.status_code == 200
    anomalies = res.json()
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0
    first = anomalies[0]
    assert "road_id" in first
    assert "flagged_as" in first
    assert first["flagged_as"] == "possible_incident"
    assert "anomaly_score" in first


def test_ai_anomalies_road_filter():
    res = client.get("/api/v1/ai/anomalies?road_id=R007")
    assert res.status_code == 200
    anomalies = res.json()
    assert isinstance(anomalies, list)
    for a in anomalies:
        assert a["road_id"] == "R007"


def test_ai_recommendations_road():
    res = client.get("/api/v1/ai/recommendations?road_id=R006")
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    assert len(recs) > 0
    first = recs[0]
    assert first["road_id"] == "R006"
    assert "recommendation_text" in first
    assert "based_on" in first
    assert "urgency" in first


def test_ai_recommendations_general():
    res = client.get("/api/v1/ai/recommendations")
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    assert len(recs) > 0
