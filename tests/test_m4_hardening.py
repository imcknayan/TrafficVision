import os
import sys
import yaml
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_production_validity():
    """Verify production docker-compose.yml exists, is valid YAML, and has all 7 services."""
    compose_path = ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "services" in config
    services = config["services"]

    required_services = [
        "postgres", "redis", "auth-service", "traffic-monitoring",
        "ai-engine", "route-analysis", "alert-service", "analytics-service", "gateway"
    ]
    for s in required_services:
        assert s in services, f"Service '{s}' missing from docker-compose.yml"

    # Verify healthchecks are defined on production services
    for s in ["postgres", "redis", "auth-service", "traffic-monitoring", "gateway"]:
        assert "healthcheck" in services[s], f"Healthcheck missing for '{s}' in production compose"


def test_docker_compose_dev_validity():
    """Verify dev docker-compose.dev.yml exists and has all microservices."""
    compose_path = ROOT / "docker-compose.dev.yml"
    assert compose_path.exists(), "docker-compose.dev.yml must exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "services" in config
    services = config["services"]

    for s in ["auth-service", "traffic-monitoring", "ai-engine", "route-analysis", "alert-service", "analytics-service", "gateway"]:
        assert s in services, f"Service '{s}' missing from docker-compose.dev.yml"


def test_env_example_completeness():
    """Verify .env.example contains all required environment variables."""
    env_path = ROOT / ".env.example"
    assert env_path.exists(), ".env.example must exist"

    content = env_path.read_text(encoding="utf-8")
    for key in [
        "DATABASE_URL", "JWT_SECRET", "AUTH_SERVICE_URL", "TRAFFIC_SERVICE_URL",
        "PREDICTION_SERVICE_URL", "ROUTE_ANALYSIS_SERVICE_URL", "ALERT_SERVICE_URL",
        "ANALYTICS_SERVICE_URL"
    ]:
        assert key in content, f"Missing key {key} in .env.example"


def test_sqlite_schema_and_indexes():
    """Verify trafficvision.db schema has all required tables and indexes."""
    db_path = ROOT / "trafficvision.db"
    assert db_path.exists(), "trafficvision.db must exist"

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Verify tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    expected_tables = {"users", "sessions", "roads", "traffic_readings", "road_conditions", "alerts"}
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    # Verify indexes
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {r[0] for r in cur.fetchall()}
    assert any("traffic" in idx for idx in indexes), "Traffic indexes must exist"
    con.close()


def test_deployment_readiness_documentation():
    """Verify DEPLOYMENT_READINESS.md exists and covers all core sections."""
    doc_path = ROOT / "DEPLOYMENT_READINESS.md"
    assert doc_path.exists(), "DEPLOYMENT_READINESS.md must exist"

    content = doc_path.read_text(encoding="utf-8")
    for section in [
        "System Architecture Overview",
        "Microservices Catalog",
        "Database Schema & Indexing",
        "Container & Docker Compose",
        "Environment Variables Configuration",
        "Security & Hardening Checklist"
    ]:
        assert section in content, f"Missing section '{section}' in DEPLOYMENT_READINESS.md"


def test_gateway_health_and_detailed_endpoint():
    """Verify Gateway /health and /health/detailed endpoints."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("m4_gateway", ROOT / "services" / "gateway" / "app" / "main.py")
    gw_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gw_mod)

    client = TestClient(gw_mod.app)
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "gateway"

    # Detailed health
    res_detailed = client.get("/health/detailed")
    assert res_detailed.status_code == 200
    det_data = res_detailed.json()
    assert "status" in det_data
    assert "dependencies" in det_data
    for svc in ["auth", "traffic", "prediction", "route_analysis", "alerts", "analytics"]:
        assert svc in det_data["dependencies"]
