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
os.environ["TRAFFIC_SERVICE_URL"] = "http://127.0.0.1:8002"
os.environ["PREDICTION_SERVICE_URL"] = "http://127.0.0.1:8003"
os.environ["ROUTE_ANALYSIS_SERVICE_URL"] = "http://127.0.0.1:8004"
os.environ["ALERT_SERVICE_URL"] = "http://127.0.0.1:8005"
os.environ["ANALYTICS_SERVICE_URL"] = "http://127.0.0.1:8006"

sys.path.insert(0, str(ROOT / "services" / "auth"))
sys.path.insert(0, str(ROOT / "services" / "traffic-monitoring"))
sys.path.insert(0, str(ROOT / "services" / "ai-engine"))
sys.path.insert(0, str(ROOT / "services" / "gateway"))
sys.path.insert(0, str(ROOT / "services" / "route-analysis"))
sys.path.insert(0, str(ROOT / "services" / "alerts"))
sys.path.insert(0, str(ROOT / "services" / "analytics"))


def run_auth_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("auth_live", ROOT / "services" / "auth" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8001, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def run_traffic_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("traffic_live", ROOT / "services" / "traffic-monitoring" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8002, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def run_ai_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ai_live", ROOT / "services" / "ai-engine" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8003, log_level="error")
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


def run_alerts_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("alerts_live", ROOT / "services" / "alerts" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8005, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def run_analytics_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("analytics_live", ROOT / "services" / "analytics" / "app" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=8006, log_level="error")
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
    t_traffic = threading.Thread(target=run_traffic_server, daemon=True)
    t_ai = threading.Thread(target=run_ai_server, daemon=True)
    t_route = threading.Thread(target=run_route_server, daemon=True)
    t_alerts = threading.Thread(target=run_alerts_server, daemon=True)
    t_analytics = threading.Thread(target=run_analytics_server, daemon=True)
    t_gw = threading.Thread(target=run_gateway_server, daemon=True)

    t_auth.start()
    t_traffic.start()
    t_ai.start()
    t_route.start()
    t_alerts.start()
    t_analytics.start()
    t_gw.start()

    # Wait for all 7 servers to respond
    ready = False
    for _ in range(40):
        try:
            r1 = httpx.get("http://127.0.0.1:8001/health", timeout=1.0)
            r2 = httpx.get("http://127.0.0.1:8002/health", timeout=1.0)
            r3 = httpx.get("http://127.0.0.1:8003/health", timeout=1.0)
            r4 = httpx.get("http://127.0.0.1:8004/health", timeout=1.0)
            r5 = httpx.get("http://127.0.0.1:8005/health", timeout=1.0)
            r6 = httpx.get("http://127.0.0.1:8006/health", timeout=1.0)
            r7 = httpx.get("http://127.0.0.1:8000/health", timeout=1.0)
            if (r1.status_code == 200 and r2.status_code == 200 and 
                r3.status_code == 200 and r4.status_code == 200 and
                r5.status_code == 200 and r6.status_code == 200 and r7.status_code == 200):
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.3)

    assert ready, "Failed to start all 7 live servers within timeout"
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


def test_live_gateway_traffic_flow():
    # 1. Live traffic through Gateway
    live = httpx.get("http://127.0.0.1:8000/api/v1/traffic/live", timeout=10.0)
    assert live.status_code == 200
    data = live.json()
    assert "data" in data
    assert len(data["data"]) > 0

    # 2. Specific road traffic
    road = httpx.get("http://127.0.0.1:8000/api/v1/traffic/road/R001", timeout=10.0)
    assert road.status_code == 200
    assert road.json()["road_id"] == "R001"

    # 3. Network density summary
    dens = httpx.get("http://127.0.0.1:8000/api/v1/traffic/density", timeout=10.0)
    assert dens.status_code == 200
    assert "average_density" in dens.json()

    # 4. Historical traffic
    hist = httpx.get("http://127.0.0.1:8000/api/v1/traffic/history?road_id=R001&limit=5", timeout=10.0)
    assert hist.status_code == 200
    assert isinstance(hist.json(), list)

    # 5. Traffic aggregation
    agg = httpx.get("http://127.0.0.1:8000/api/v1/traffic/aggregate?road_id=R001&granularity=hour", timeout=10.0)
    assert agg.status_code == 200
    assert isinstance(agg.json(), list)

    # 6. Road condition
    rc = httpx.get("http://127.0.0.1:8000/api/v1/traffic/road-condition/R001", timeout=10.0)
    assert rc.status_code == 200
    assert rc.json()["road_id"] == "R001"
    assert "status" in rc.json()


def test_live_gateway_prediction_flow():
    # 1. Congestion prediction through Gateway
    pred = httpx.get("http://127.0.0.1:8000/api/v1/predict/congestion?road_id=R001", timeout=10.0)
    assert pred.status_code == 200
    data = pred.json()
    assert data["road_id"] == "R001"
    assert "predicted_level" in data
    assert "confidence" in data
    assert data["model_version"] == "model-v2-rf"

    # 2. Delay prediction through Gateway
    delay = httpx.get("http://127.0.0.1:8000/api/v1/predict/delay?road_id=R001&distance_km=5.0", timeout=10.0)
    assert delay.status_code == 200
    assert "estimated_delay_minutes" in delay.json()

    # 3. Peak-hour prediction through Gateway
    peak = httpx.get("http://127.0.0.1:8000/api/v1/predict/peak-hours?road_id=R006", timeout=10.0)
    assert peak.status_code == 200
    assert "peak_windows" in peak.json()


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
    assert ranked_list[0]["rank"] == 1
    assert ranked_list[0]["is_recommended"] is True


def test_live_gateway_alerts_flow():
    # 1. Create alert via Gateway
    create_res = httpx.post(
        "http://127.0.0.1:8000/api/v1/alerts",
        json={
            "type": "congestion",
            "severity": "HIGH",
            "road_id": "R001",
            "message": "Heavy congestion detected on Main Expressway via Gateway E2E",
        },
        timeout=10.0,
    )
    assert create_res.status_code == 201
    created_alert = create_res.json()
    assert created_alert["road_id"] == "R001"
    alert_id = created_alert.get("alert_id") or created_alert.get("id")
    assert alert_id is not None

    # 2. Get active alerts via Gateway
    active_res = httpx.get("http://127.0.0.1:8000/api/v1/alerts/active", timeout=10.0)
    assert active_res.status_code == 200
    active_list = active_res.json()
    assert isinstance(active_list, list)
    assert any(a["id"] == alert_id for a in active_list)

    # 3. Mark alert as read via Gateway
    read_res = httpx.post(f"http://127.0.0.1:8000/api/v1/alerts/{alert_id}/read", timeout=10.0)
    read_data = read_res.json()
    assert (read_data.get("read") is True) or (read_data.get("is_read") is True)


def test_live_gateway_analytics_and_ai_insights_flow():
    # 1. Traffic Trends via Gateway
    trends = httpx.get("http://127.0.0.1:8000/api/v1/analytics/trends?road_id=R001&range=day", timeout=10.0)
    assert trends.status_code == 200
    t_data = trends.json()
    assert t_data["road_id"] == "R001"
    assert "points" in t_data
    assert len(t_data["points"]) > 0

    # 2. Traffic Heatmap via Gateway
    heatmap = httpx.get("http://127.0.0.1:8000/api/v1/analytics/heatmap?range=day", timeout=10.0)
    assert heatmap.status_code == 200
    h_data = heatmap.json()
    assert "roads" in h_data
    assert "time_buckets" in h_data
    assert "values" in h_data

    # 3. Analytics Report export via Gateway
    rep = httpx.get("http://127.0.0.1:8000/api/v1/analytics/reports?format=json", timeout=10.0)
    assert rep.status_code == 200
    rep_data = rep.json()
    assert "data" in rep_data
    assert "record_count" in rep_data

    # 4. AI Anomalies via Gateway
    anom = httpx.get("http://127.0.0.1:8000/api/v1/ai/anomalies", timeout=10.0)
    assert anom.status_code == 200
    a_data = anom.json()
    assert isinstance(a_data, list)
    assert len(a_data) > 0
    assert "anomaly_score" in a_data[0]

    # 5. AI Recommendations via Gateway
    rec = httpx.get("http://127.0.0.1:8000/api/v1/ai/recommendations", timeout=10.0)
    assert rec.status_code == 200
    r_data = rec.json()
    assert isinstance(r_data, list)
    assert len(r_data) > 0
    assert "recommendation_text" in r_data[0]


def test_live_gateway_detailed_health():
    res = httpx.get("http://127.0.0.1:8000/health/detailed", timeout=10.0)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    deps = data["dependencies"]
    for svc in ["auth", "traffic", "prediction", "route_analysis", "alerts", "analytics"]:
        assert deps[svc] == "healthy"

