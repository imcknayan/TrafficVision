import os
import sys
import time
import threading
import uvicorn
import httpx
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'test_e2e.db'}"
os.environ["JWT_SECRET"] = "e2e-live-test-secret"
os.environ["AUTH_SERVICE_URL"] = "http://127.0.0.1:8001"
os.environ["ROUTE_ANALYSIS_SERVICE_URL"] = "http://127.0.0.1:8004"

sys.path.insert(0, str(ROOT / "services" / "auth"))
sys.path.insert(0, str(ROOT / "services" / "gateway"))
sys.path.insert(0, str(ROOT / "services" / "route-analysis"))


def run_auth_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("auth_live", ROOT / "services" / "auth" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8001, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def run_route_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ra_live", ROOT / "services" / "route-analysis" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8004, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def run_gateway_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gw_live", ROOT / "services" / "gateway" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    server.run()


@pytest.fixture(scope="module", autouse=True)
def live_services():
    t_auth = threading.Thread(target=run_auth_server, daemon=True)
    t_route = threading.Thread(target=run_route_server, daemon=True)
    t_gw = threading.Thread(target=run_gateway_server, daemon=True)

    t_auth.start()
    t_route.start()
    t_gw.start()

    # Wait for all 3 servers to respond
    ready = False
    for _ in range(30):
        try:
            r1 = httpx.get("http://127.0.0.1:8001/health", timeout=1.0)
            r2 = httpx.get("http://127.0.0.1:8004/health", timeout=1.0)
            r3 = httpx.get("http://127.0.0.1:8000/health", timeout=1.0)
            if r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.3)

    assert ready, "Failed to start live servers within timeout"
    yield

    # Clean up test_e2e.db
    db_file = ROOT / "test_e2e.db"
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass


def test_live_gateway_health():
    res = httpx.get("http://127.0.0.1:8000/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "gateway"}


def test_live_gateway_cors_preflight():
    res = httpx.options(
        "http://127.0.0.1:8000/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:5500")


def test_live_gateway_auth_flow():
    unique_email = f"alice_{int(time.time() * 1000)}@live.com"
    # 1. Register with role='user' through Gateway port 8000
    reg = httpx.post(
        "http://127.0.0.1:8000/api/v1/auth/register",
        json={"name": "Alice Public", "email": unique_email, "password": "password123", "role": "user"},
    )
    assert reg.status_code == 201
    assert "user_id" in reg.json()

    # 2. Login through Gateway port 8000
    login = httpx.post(
        "http://127.0.0.1:8000/api/v1/auth/login",
        json={"email": unique_email, "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["role"] == "public"
    assert tokens["name"] == "Alice Public"
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 3. GET /auth/me through Gateway with Bearer token
    me = httpx.get(
        "http://127.0.0.1:8000/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["name"] == "Alice Public"
    assert me.json()["role"] == "public"

    # 4. Refresh token through Gateway
    ref = httpx.post(
        "http://127.0.0.1:8000/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert ref.status_code == 200
    assert "access_token" in ref.json()


def test_live_gateway_route_flow():
    # 1. Route Optimize through Gateway
    opt = httpx.get(
        "http://127.0.0.1:8000/api/v1/route/optimize",
        params={"origin": "26.144276,91.736153", "destination": "26.115802,91.708609"},
        timeout=25.0,
    )
    assert opt.status_code == 200
    opt_data = opt.json()
    assert "route_id" in opt_data
    assert "path" in opt_data
    assert "distance_km" in opt_data
    assert "congestion_score" in opt_data

    # 2. Route Travel Time through Gateway
    tt = httpx.get(
        "http://127.0.0.1:8000/api/v1/route/travel-time",
        params={"route_id": opt_data["route_id"]},
        timeout=25.0,
    )
    assert tt.status_code == 200
    assert "estimated_minutes" in tt.json()

    # 3. Alternate Routes through Gateway
    alt = httpx.get(
        "http://127.0.0.1:8000/api/v1/route/alternate",
        params={"origin": "26.144276,91.736153", "destination": "26.115802,91.708609"},
        timeout=25.0,
    )
    assert alt.status_code == 200
    alt_data = alt.json()
    assert isinstance(alt_data, list)
    assert len(alt_data) >= 1
    assert "rank" in alt_data[0]

    # 4. Road Conditions through Gateway
    cond = httpx.get(
        "http://127.0.0.1:8000/api/v1/route/conditions",
        params={"road_id": "R001"},
        timeout=25.0,
    )
    assert cond.status_code == 200
    assert cond.json()["road_id"] == "R001"
    assert "status" in cond.json()

    # 5. Route Ranking POST through Gateway
    rank = httpx.post(
        "http://127.0.0.1:8000/api/v1/route/rank",
        json={
            "routes": [
                {"route_id": "rB", "distance_km": 12.0, "roads": ["R003"], "base_duration_minutes": 16.0},
                {"route_id": "rA", "distance_km": 4.5, "roads": ["R001"], "base_duration_minutes": 6.0},
            ]
        },
        timeout=25.0,
    )
    assert rank.status_code == 200
    ranked_list = rank.json()
    assert isinstance(ranked_list, list)
    assert len(ranked_list) == 2
    assert ranked_list[0]["route_id"] == "rA"
    assert ranked_list[0]["rank"] == 1
    assert ranked_list[0]["is_recommended"] is True
