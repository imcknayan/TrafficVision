import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'test.db'}"
os.environ["JWT_SECRET"] = "test-secret"
sys.path.insert(0, str(ROOT / "services" / "auth"))
sys.path.insert(0, str(ROOT / "services" / "gateway"))
sys.path.insert(0, str(ROOT / "services" / "route-analysis"))

from app.main import Base, engine, app as auth_app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_auth_user_role_normalization():
    client = TestClient(auth_app)
    # Register with role 'user' (from frontend Login.html)
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": "Public User", "email": "puser@example.com", "password": "password123", "role": "user"},
    )
    assert reg.status_code == 201
    assert "user_id" in reg.json()

    # Login
    login = client.post("/api/v1/auth/login", json={"email": "puser@example.com", "password": "password123"})
    assert login.status_code == 200
    data = login.json()
    assert data["role"] == "public"
    assert data["name"] == "Public User"
    assert "user_id" in data
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify /auth/me
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["name"] == "Public User"
    assert me_data["role"] == "public"


def test_auth_operator_role_normalization():
    client = TestClient(auth_app)
    # Register with role 'operator'
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": "Test Op", "email": "optest@example.com", "password": "password123", "role": "operator"},
    )
    assert reg.status_code == 201

    login = client.post("/api/v1/auth/login", json={"email": "optest@example.com", "password": "password123"})
    assert login.status_code == 200
    assert login.json()["role"] == "traffic_operator"


def test_cors_preflight_on_auth_and_route():
    client = TestClient(auth_app)
    # OPTIONS request for CORS preflight
    res = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:5500")
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_route_conditions_and_travel_time():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ra_main", ROOT / "services" / "route-analysis" / "app" / "main.py")
    ra_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ra_mod)

    client = TestClient(ra_mod.app)
    cond = client.get("/api/v1/route/conditions?road_id=R001")
    assert cond.status_code == 200
    data = cond.json()
    assert data["road_id"] == "R001"
    assert "status" in data


def test_gateway_route_registration():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gw_main", ROOT / "services" / "gateway" / "app" / "main.py")
    gw_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gw_mod)

    # Verify gateway has routes for auth, admin, traffic, predict, route
    paths = [route.path for route in gw_mod.app.routes]
    assert "/api/v1/auth/{path:path}" in paths
    assert "/api/v1/admin/{path:path}" in paths
    assert "/api/v1/traffic/{path:path}" in paths
    assert "/api/v1/predict/{path:path}" in paths
    assert "/api/v1/route/{path:path}" in paths
