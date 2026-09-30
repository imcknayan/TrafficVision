import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
import importlib.util

spec_db = importlib.util.spec_from_file_location("traffic_db", ROOT / "services" / "traffic-monitoring" / "app" / "database.py")
db_mod = importlib.util.module_from_spec(spec_db)
sys.modules["traffic_db"] = db_mod
spec_db.loader.exec_module(db_mod)

spec_seed = importlib.util.spec_from_file_location("traffic_seed", ROOT / "services" / "traffic-monitoring" / "app" / "seed_data.py")
seed_mod = importlib.util.module_from_spec(spec_seed)
sys.modules["traffic_seed"] = seed_mod
spec_seed.loader.exec_module(seed_mod)

spec_main = importlib.util.spec_from_file_location("traffic_main_svc", ROOT / "services" / "traffic-monitoring" / "app" / "main.py")
traffic_mod = importlib.util.module_from_spec(spec_main)
sys.modules["traffic_main_svc"] = traffic_mod
spec_main.loader.exec_module(traffic_mod)

app = traffic_mod.app
Base = db_mod.Base
engine = db_mod.engine
SessionLocal = db_mod.SessionLocal
seed_database = seed_mod.seed_database

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield


def test_traffic_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "traffic-monitoring"}


def test_get_live_traffic():
    res = client.get("/api/v1/traffic/live")
    assert res.status_code == 200
    body = res.json()
    assert "updated_at" in body
    assert "count" in body
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    first = body["data"][0]
    assert "road_id" in first
    assert "road_name" in first
    assert "vehicle_count" in first
    assert "average_speed" in first
    assert "density" in first
    assert "congestion_level" in first


def test_get_road_traffic():
    res = client.get("/api/v1/traffic/road/R001")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R001"
    assert "road_name" in data
    assert "vehicle_count" in data
    assert "average_speed" in data
    assert "density" in data
    assert "congestion_level" in data


def test_get_road_traffic_not_found():
    res = client.get("/api/v1/traffic/road/nonexistent-road-xyz")
    assert res.status_code == 404


def test_traffic_density_summary():
    res = client.get("/api/v1/traffic/density")
    assert res.status_code == 200
    data = res.json()
    assert "average_density" in data
    assert "total_vehicle_count" in data
    assert "total_roads" in data
    assert "high_congestion_roads" in data
    assert isinstance(data["high_congestion_roads"], list)


def test_traffic_history():
    res = client.get("/api/v1/traffic/history?road_id=R001&limit=5")
    assert res.status_code == 200
    readings = res.json()
    assert isinstance(readings, list)
    assert len(readings) <= 5
    if readings:
        item = readings[0]
        assert item["road_id"] == "R001"
        assert "timestamp" in item
        assert "vehicle_count" in item
        assert "density" in item
        assert "congestion_level" in item


def test_traffic_aggregate_hourly():
    res = client.get("/api/v1/traffic/aggregate?road_id=R001&granularity=hour")
    assert res.status_code == 200
    aggs = res.json()
    assert isinstance(aggs, list)
    assert len(aggs) > 0
    item = aggs[0]
    assert item["road_id"] == "R001"
    assert "bucket" in item
    assert "avg_vehicle_count" in item
    assert "avg_density" in item
    assert "avg_speed" in item
    assert "dominant_congestion_level" in item


def test_traffic_road_condition():
    res = client.get("/api/v1/traffic/road-condition/R001")
    assert res.status_code == 200
    data = res.json()
    assert data["road_id"] == "R001"
    assert "status" in data
    assert "notes" in data
    assert "updated_at" in data
