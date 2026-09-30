import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8001")
TRAFFIC_SERVICE_URL = os.getenv("TRAFFIC_SERVICE_URL", "http://127.0.0.1:8002")
PREDICTION_SERVICE_URL = os.getenv("PREDICTION_SERVICE_URL", "http://127.0.0.1:8003")
ROUTE_ANALYSIS_SERVICE_URL = os.getenv("ROUTE_ANALYSIS_SERVICE_URL", "http://127.0.0.1:8004")
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://127.0.0.1:8005")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://127.0.0.1:8006")
app = FastAPI(title="TrafficVision AI API Gateway", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/health/detailed")
async def detailed_health():
    services = {
        "auth": os.getenv("AUTH_SERVICE_URL", AUTH_SERVICE_URL),
        "traffic": os.getenv("TRAFFIC_SERVICE_URL", TRAFFIC_SERVICE_URL),
        "prediction": os.getenv("PREDICTION_SERVICE_URL", PREDICTION_SERVICE_URL),
        "route_analysis": os.getenv("ROUTE_ANALYSIS_SERVICE_URL", ROUTE_ANALYSIS_SERVICE_URL),
        "alerts": os.getenv("ALERT_SERVICE_URL", ALERT_SERVICE_URL),
        "analytics": os.getenv("ANALYTICS_SERVICE_URL", ANALYTICS_SERVICE_URL),
    }
    status_map = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in services.items():
            try:
                res = await client.get(f"{url}/health")
                status_map[name] = "healthy" if res.status_code == 200 else f"unhealthy ({res.status_code})"
            except Exception:
                status_map[name] = "unreachable"
    overall = "healthy" if all(v == "healthy" for v in status_map.values()) else "degraded"
    return {"status": overall, "service": "gateway", "dependencies": status_map}


async def forward(request: Request, base_url: str, path: str):
    target = f"{base_url}/{path}" if path else base_url
    headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            upstream = await client.request(request.method, target, params=request.query_params, content=await request.body(), headers=headers)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
    return Response(content=upstream.content, status_code=upstream.status_code, headers={k: v for k, v in upstream.headers.items() if k.lower() not in {"content-length", "transfer-encoding", "connection"}}, media_type=upstream.headers.get("content-type"))


@app.api_route("/api/v1/auth", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def auth_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/auth/{path}" if path else "api/v1/auth"
    return await forward(request, os.getenv("AUTH_SERVICE_URL", AUTH_SERVICE_URL), target_path)


@app.api_route("/api/v1/admin", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def admin_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/admin/{path}" if path else "api/v1/admin"
    return await forward(request, os.getenv("AUTH_SERVICE_URL", AUTH_SERVICE_URL), target_path)


@app.api_route("/api/v1/traffic", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/traffic/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def traffic_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/traffic/{path}" if path else "api/v1/traffic"
    return await forward(request, os.getenv("TRAFFIC_SERVICE_URL", TRAFFIC_SERVICE_URL), target_path)


@app.api_route("/api/v1/predict", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/predict/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def predict_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/predict/{path}" if path else "api/v1/predict"
    return await forward(request, os.getenv("PREDICTION_SERVICE_URL", PREDICTION_SERVICE_URL), target_path)


@app.api_route("/api/v1/route", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/route/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def route_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/route/{path}" if path else "api/v1/route"
    return await forward(request, os.getenv("ROUTE_ANALYSIS_SERVICE_URL", ROUTE_ANALYSIS_SERVICE_URL), target_path)


@app.api_route("/api/v1/alerts", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/alerts/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def alerts_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/alerts/{path}" if path else "api/v1/alerts"
    return await forward(request, os.getenv("ALERT_SERVICE_URL", ALERT_SERVICE_URL), target_path)


@app.api_route("/api/v1/analytics", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/analytics/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def analytics_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/analytics/{path}" if path else "api/v1/analytics"
    return await forward(request, os.getenv("ANALYTICS_SERVICE_URL", ANALYTICS_SERVICE_URL), target_path)


@app.api_route("/api/v1/ai", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/api/v1/ai/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ai_gateway(request: Request, path: str = ""):
    target_path = f"api/v1/ai/{path}" if path else "api/v1/ai"
    return await forward(request, os.getenv("PREDICTION_SERVICE_URL", PREDICTION_SERVICE_URL), target_path)


