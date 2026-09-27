# TrafficVision AI - Milestone 1 Backend Starter

This is an independent M1 starter until the Team-5 repository link is available. It preserves the SRS paths:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/traffic/live`, `/road/{road_id}`, `/density` (gateway integration routes)
- `GET /api/v1/predict/congestion?road_id={id}` (gateway integration route)

## Run locally

1. Install Python 3.12+, then run `pip install -r requirements.txt`.
2. Run the Auth service: `uvicorn app.main:app --app-dir services/auth --port 8001 --reload`.
3. Run the gateway in a second terminal: `uvicorn app.main:app --app-dir services/gateway --port 8000 --reload`.
4. Open `http://localhost:8001/docs` for Auth Swagger and `http://localhost:8000/docs` for the Gateway.
5. Run tests: `pytest`.

For PostgreSQL and Redis, create a `.env` from `.env.example`, set a real `JWT_SECRET`, and run `docker compose -f docker-compose.dev.yml up --build`.

## Team integration remaining

Intern 2 must supply the Traffic Monitoring service at `TRAFFIC_SERVICE_URL` with the frozen `/api/v1/traffic/*` paths. Intern 3 must supply the AI Engine at `PREDICTION_SERVICE_URL` with `/api/v1/predict/congestion`. Once their containers/service names are known, update these two environment values and include them in the shared Compose file. Intern 5 owns CI, Compose validation, and the final integration test cycle.

Before merging into Team-5's repository, compare filenames, dependency versions, and any existing migrations; do not overwrite teammates' monitoring/prediction code.

## Milestone 2 - Backend & Integration

### Route Analysis Service

The Route Analysis Service provides backend APIs for route optimization,
alternate route analysis, travel-time estimation, and road-condition lookup.

### Implemented APIs

- `GET /api/v1/route/optimize`
- `GET /api/v1/route/alternate`
- `GET /api/v1/route/travel-time`
- `GET /api/v1/route/conditions`

### Integration

The API Gateway forwards route requests to the Route Analysis Service.

Local development flow:

Client -> API Gateway (8000) -> Route Analysis (8004) -> OSRM

The Route Analysis Service uses the OSRM public routing service based on
OpenStreetMap road data.

### Validation

### Validation

The following Route Analysis APIs were tested successfully locally:

- Route optimization: PASS
- Alternate route: PASS
- Travel-time estimation: PASS
- Road-condition endpoint: PASS

Automated tests:

- 3/3 tests passed
- Test execution time: 1.51 seconds
- 19 deprecation warnings reported

Example successful route:

- Route ID: `route-ca624d0c7a10`
- Distance: `5.39 km`
- Estimated travel time: `7.9 minutes`

### Current Limitation

The current congestion score uses a distance-based fallback while the
trained AI/ML prediction service integration is pending.

The road-condition endpoint currently returns an `unknown` status when
the upstream traffic-condition feed is unavailable.
