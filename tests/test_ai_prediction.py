import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
import importlib.util

spec = importlib.util.spec_from_file_location("ai_engine_main", ROOT / "services" / "ai-engine" / "app" / "main.py")
ai_mod = importlib.util.module_from_spec(spec)
sys.modules["ai_engine_main"] = ai_mod
spec.loader.exec_module(ai_mod)

app = ai_mod.app
load_model = ai_mod.load_model

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_ai_engine():
    load_model()
    yield


def test_ai_engine_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-engine"
    assert "model_version" in data


def test_model_info():
    res = client.get("/api/v1/predict/model-info")
    assert res.status_code == 200
    info = res.json()
    assert info["model_version"] == "model-v2-rf"
    assert "metrics" in info or "test_accuracy" in str(info)


def test_predict_congestion():
    res = client.get("/api/v1/predict/congestion?road_id=R001")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R001"
    assert "predicted_level" in data
    assert "confidence" in data
    assert data["confidence"] > 0.0
    assert data["model_version"] == "model-v2-rf"
    assert "current_density" in data


def test_predict_congestion_high_density():
    res = client.get("/api/v1/predict/congestion?road_id=R007&vehicle_count=290&average_speed=10.0")
    assert res.status_code == 200
    data = res.json()
    assert data["predicted_level"] in ("High", "Severe")
    assert data["confidence"] >= 0.6


def test_predict_delay():
    res = client.get("/api/v1/predict/delay?road_id=R001&distance_km=5.0")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R001"
    assert "estimated_delay_minutes" in data
    assert "delay_minutes" in data
    assert "confidence" in data
    assert data["model_version"] == "model-v2-rf"


def test_predict_peak_hours():
    res = client.get("/api/v1/predict/peak-hours?road_id=R006")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R006"
    assert "peak_windows" in data
    assert isinstance(data["peak_windows"], list)
    assert len(data["peak_windows"]) > 0
    first_window = data["peak_windows"][0]
    assert "start" in first_window
    assert "end" in first_window
    assert "model_version" in data
