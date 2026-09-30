# TrafficVision AI — Production Deployment Readiness & Architecture Specification (Milestone 4)

## 1. System Architecture Overview

TrafficVision AI is an enterprise-grade, distributed smart traffic prediction, congestion management, and route optimization platform. The system operates on an asynchronous microservices architecture orchestrated via FastAPI, Docker Compose, PostgreSQL 16, Redis 7, and Scikit-Learn machine learning pipelines.

```
                                    +--------------------+
                                    |    Client UI       |
                                    | (HTML5/ES6/Chart)  |
                                    +---------+----------+
                                              |
                                              v [Port 8000]
                                   +----------------------+
                                   |  API Gateway Router  |
                                   +----+---+---+---+---+--+
                                        |   |   |   |   |
         +------------------------------+   |   |   |   +-------------------------------+
         |                  +---------------+   |   +-------------------+               |
         v [Port 8001]      v [Port 8002]       v [Port 8003]           v [Port 8004]   v [Port 8005/8006]
   +-----------+    +------------------+    +-----------+        +------------+    +----------------+
   |   Auth    |    | Traffic Monitor  |    | AI Engine |        | Route Opt  |    | Alerts &       |
   | & RBAC    |    | & Data Engine    |    | (ML/RF)   |        | (OSRM)     |    | Analytics      |
   +-----+-----+    +--------+---------+    +-----+-----+        +------+-----+    +-------+--------+
         |                   |                    |                     |                  |
         +-------------------+--------------------+---------------------+------------------+
                             |
                   +---------v---------+
                   |  PostgreSQL 16    |
                   |  & Redis Cache    |
                   +-------------------+
```

---

## 2. Microservices Catalog

| Service Name | Port | Primary Responsibilities | Health Endpoint |
|---|---|---|---|
| **API Gateway** | 8000 | Reverse proxy, dynamic upstream routing, CORS, unified health aggregation | `GET /health`, `GET /health/detailed` |
| **Auth Service** | 8001 | JWT issuance, password hashing (bcrypt), token refresh, RBAC authorization | `GET /health` |
| **Traffic Monitoring** | 8002 | Real-time traffic, 28-day historical time-series (7,403 rows), aggregations, road conditions | `GET /health` |
| **AI Prediction Engine** | 8003 | Random Forest Classifier (congestion), Random Forest Regressor (delay), anomaly detection | `GET /health` |
| **Route Analysis** | 8004 | Multi-criteria route optimization, OSRM routing, congestion penalty scoring | `GET /health` |
| **Alert Service** | 8005 | Incident alerts, congestion notifications, user read status tracking | `GET /health` |
| **Analytics Service** | 8006 | Hourly/daily trend analysis, 7x24 congestion heatmaps, CSV/JSON report exports | `GET /health` |

---

## 3. Database Schema & Indexing Hardening

The system employs PostgreSQL 16 (production) with dual-mode SQLite support for zero-dependency local testing.

### Key Tables
1. `users`: Stores user identity, bcrypt password hashes, and RBAC roles (`admin`, `traffic_operator`, `public`).
2. `sessions`: Refresh token rotation tracking with JTI UUIDs and revocation timestamps.
3. `roads`: Corridor definitions, physical road capacities, base speeds.
4. `traffic_readings`: Time-series sensor telemetry (7,403 records) including vehicle count, speed, density, and congestion level.
5. `road_conditions`: Dynamic hazard, construction, weather, and incident advisories.
6. `alerts`: System notifications, severity levels (`CRITICAL`, `WARNING`, `INFO`), and read statuses.

### Production Indexes
- `idx_traffic_road_time`: Composite index on `traffic_readings(road_id, recorded_at DESC)` for sub-millisecond road history lookups.
- `idx_traffic_time`: Index on `traffic_readings(recorded_at DESC)` for platform-wide live queries.
- `idx_traffic_road_time_level`: Composite index for fast congestion level distribution filtering.
- `idx_alerts_road_created`: Composite index on `alerts(road_id, created_at DESC)` for active corridor alerts.
- `idx_sessions_user_id`: Index on `sessions(user_id)` for rapid token revocation during logout.

---

## 4. Container & Docker Compose Specifications

Two container compose configurations are maintained:
1. `docker-compose.yml`: Production configuration with health checks, restart policies (`unless-stopped`), isolated bridge network, and persistent storage volumes.
2. `docker-compose.dev.yml`: Development configuration with volume mounts for rapid local iteration.

### Container Health Check Definitions
Each microservice container exposes a container-level health probe:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:<PORT>/health')"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 10s
```

PostgreSQL and Redis utilize native health probes:
- Postgres: `pg_isready -U trafficvision -d trafficvision`
- Redis: `redis-cli ping`

---

## 5. Environment Variables Configuration

| Variable | Description | Production Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg://trafficvision:trafficvision@postgres:5432/trafficvision` |
| `REDIS_URL` | Redis cache connection string | `redis://redis:6379/0` |
| `JWT_SECRET` | 256-bit symmetric key for HMAC-SHA256 tokens | Must be set to high-entropy secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifespan | `7` |
| `AUTH_SERVICE_URL` | Gateway target for auth service | `http://auth-service:8001` |
| `TRAFFIC_SERVICE_URL` | Gateway target for traffic service | `http://traffic-monitoring:8002` |
| `PREDICTION_SERVICE_URL` | Gateway target for AI prediction | `http://ai-engine:8003` |
| `ROUTE_ANALYSIS_SERVICE_URL` | Gateway target for route optimization | `http://route-analysis:8004` |
| `ALERT_SERVICE_URL` | Gateway target for alert notifications | `http://alert-service:8005` |
| `ANALYTICS_SERVICE_URL` | Gateway target for traffic analytics | `http://analytics-service:8006` |
| `OSRM_BASE_URL` | OpenStreetMap routing engine base URL | `https://router.project-osrm.org` |

---

## 6. Security & Hardening Checklist

- [x] **No Secrets in Source Control**: Passwords and secrets are injected strictly via environment variables. `.env` is ignored by git.
- [x] **Bcrypt Password Hashing**: Passwords stored as 60-character salted bcrypt hashes.
- [x] **Stateless JWT + Rotating Refresh Tokens**: Revocation tracked via `jti` in database sessions table.
- [x] **Role-Based Access Control (RBAC)**: Fine-grained endpoints restricted to `admin`, `traffic_operator`, or `public`.
- [x] **CORS Middleware**: Explicit CORS middleware configured across all microservices.
- [x] **Query Parameter Validation**: Strict Pydantic and FastAPI `Query`/`Path` parameter regex constraints.
- [x] **Graceful Fallbacks**: Route analysis and AI engine provide deterministic statistical fallbacks if remote external services are offline.
