import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Query, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session
from jose import jwt, JWTError

try:
    from app.database import Base, Alert, engine, SessionLocal, get_db, init_db
except (ImportError, AttributeError, ModuleNotFoundError):
    import importlib.util
    from pathlib import Path
    _db_path = Path(__file__).resolve().parent / "database.py"
    _spec = importlib.util.spec_from_file_location("alerts_database", _db_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    Base = _mod.Base
    Alert = _mod.Alert
    engine = _mod.engine
    SessionLocal = _mod.SessionLocal
    get_db = _mod.get_db
    init_db = _mod.init_db

JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-me")
ALGORITHM = "HS256"

app = FastAPI(
    title="TrafficVision AI Alert & Notification Service",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INITIAL_ALERTS = [
    {
        "id": "alert-init-001",
        "type": "hazard",
        "severity": "critical",
        "road_id": "R007",
        "message": "Harbor Tunnel Approach: Hazard reported - tunnel maintenance work underway, lane 2 closed.",
    },
    {
        "id": "alert-init-002",
        "type": "congestion",
        "severity": "high",
        "road_id": "R006",
        "message": "Airport Corridor: Heavy departure congestion detected. Expect 15-20 min delays.",
    },
    {
        "id": "alert-init-003",
        "type": "closure",
        "severity": "medium",
        "road_id": "R005",
        "message": "Industrial Highway: Right lane closed for scheduled surface repaving.",
    },
    {
        "id": "alert-init-004",
        "type": "accident",
        "severity": "high",
        "road_id": "R003",
        "message": "West Ring Road: Minor vehicle incident near northern interchange cleared to shoulder.",
    },
]


def seed_initial_alerts(db: Session):
    init_db()
    if db.query(Alert).count() == 0:
        for item in INITIAL_ALERTS:
            alert = Alert(
                id=item["id"],
                type=item["type"],
                severity=item["severity"],
                road_id=item["road_id"],
                message=item["message"],
                is_read=False,
                created_at=datetime.now(timezone.utc),
            )
            db.add(alert)
        db.commit()


@app.on_event("startup")
def startup_event():
    init_db()
    with SessionLocal() as db:
        seed_initial_alerts(db)


class CreateAlertRequest(BaseModel):
    type: str = Field(..., description="Alert type: congestion, accident, closure, delay, hazard")
    severity: str = Field(..., description="Alert severity: low, medium, high, critical")
    road_id: str = Field(..., description="Monitored road segment ID")
    message: str = Field(..., min_length=3, description="Alert description text")


def extract_role(authorization: Optional[str], query_role: Optional[str]) -> str:
    if query_role:
        return query_role.strip().lower()
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
            return str(payload.get("role", "public")).lower()
        except JWTError:
            pass
    return "admin"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "alerts",
        "database": "connected",
    }


@app.post("/api/v1/alerts", status_code=status.HTTP_201_CREATED)
def create_alert(payload: CreateAlertRequest, db: Session = Depends(get_db)):
    """
    SRS 7.1: POST /api/v1/alerts (internal) — { type, severity, road_id, message } → 201 { alert_id }
    Called by congestion threshold feed and anomaly detection feed.
    """
    alert_id = f"alert-{uuid.uuid4().hex[:10]}"
    alert = Alert(
        id=alert_id,
        type=payload.type.strip().lower(),
        severity=payload.severity.strip().lower(),
        road_id=payload.road_id.strip(),
        message=payload.message.strip(),
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "alert_id": alert.id,
        "id": alert.id,
        "type": alert.type,
        "severity": alert.severity,
        "road_id": alert.road_id,
        "created_at": alert.created_at.isoformat(),
        "status": "created",
    }


@app.get("/api/v1/alerts/my")
def get_my_alerts(
    role: Optional[str] = Query(None, description="Optional user role override: admin, operator, public"),
    authorization: Optional[str] = Header(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    SRS 7.1: GET /api/v1/alerts/my → 200 [ { alert_id, type, severity, road_id, message, read, created_at } ]
    Role-scoped for the current user.
    """
    user_role = extract_role(authorization, role)
    query = db.query(Alert)

    if user_role in ("public", "commuter", "user"):
        # Public users see critical / high alerts, or accidents/closures
        query = query.filter(
            (Alert.severity.in_(["high", "critical"])) |
            (Alert.type.in_(["accident", "closure", "hazard"]))
        )

    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()

    return [
        {
            "alert_id": a.id,
            "id": a.id,
            "type": a.type,
            "severity": a.severity,
            "road_id": a.road_id,
            "message": a.message,
            "read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@app.post("/api/v1/alerts/{alert_id}/read")
def mark_alert_read(alert_id: str, db: Session = Depends(get_db)):
    """
    SRS 7.1: POST /api/v1/alerts/{alert_id}/read → 200 { alert_id, read: true }
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    alert.is_read = True
    db.commit()

    return {
        "alert_id": alert.id,
        "read": True,
    }


@app.get("/api/v1/alerts/active")
def get_active_alerts(
    road_id: Optional[str] = Query(None, description="Filter by road ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    SRS 7.1: GET /api/v1/alerts/active → 200 list of currently active alerts for Admin/Operator dashboards.
    """
    query = db.query(Alert).filter(Alert.is_read == False)
    if road_id:
        query = query.filter(Alert.road_id == road_id)

    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()

    return [
        {
            "alert_id": a.id,
            "id": a.id,
            "type": a.type,
            "severity": a.severity,
            "road_id": a.road_id,
            "message": a.message,
            "read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]
