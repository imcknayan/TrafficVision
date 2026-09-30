import os
from datetime import datetime, timezone
from typing import Optional, List
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

try:
    from app.database import (
        Base, Road, TrafficReading, RoadCondition,
        engine, SessionLocal, get_db, init_db
    )
    from app.seed_data import seed_database, ROADS_DATA
except (ImportError, AttributeError, ModuleNotFoundError):
    import importlib.util
    from pathlib import Path
    _db_path = Path(__file__).resolve().parent / "database.py"
    _spec = importlib.util.spec_from_file_location("traffic_database", _db_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    Base = _mod.Base
    Road = _mod.Road
    TrafficReading = _mod.TrafficReading
    RoadCondition = _mod.RoadCondition
    engine = _mod.engine
    SessionLocal = _mod.SessionLocal
    get_db = _mod.get_db
    init_db = _mod.init_db

    _seed_path = Path(__file__).resolve().parent / "seed_data.py"
    _seed_spec = importlib.util.spec_from_file_location("traffic_seed_data", _seed_path)
    _seed_mod = importlib.util.module_from_spec(_seed_spec)
    _seed_spec.loader.exec_module(_seed_mod)
    seed_database = _seed_mod.seed_database
    ROADS_DATA = _seed_mod.ROADS_DATA

app = FastAPI(
    title="TrafficVision Traffic Monitoring Service",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()
    with SessionLocal() as db:
        if db.query(Road).count() == 0 or db.query(TrafficReading).count() == 0:
            seed_database(db)


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "traffic-monitoring",
    }


def get_latest_reading_for_road(db: Session, road_id: str) -> Optional[TrafficReading]:
    return (
        db.query(TrafficReading)
        .filter(TrafficReading.road_id == road_id)
        .order_by(desc(TrafficReading.recorded_at))
        .first()
    )


@app.get("/api/v1/traffic/live")
def live_traffic(db: Session = Depends(get_db)):
    """
    Return current traffic information for all monitored roads.
    """
    roads = db.query(Road).all()
    timestamp = current_timestamp()
    results = []

    for road in roads:
        latest = get_latest_reading_for_road(db, road.road_id)
        if latest:
            results.append({
                "road_id": road.road_id,
                "road_name": road.road_name,
                "vehicle_count": latest.vehicle_count,
                "average_speed": latest.average_speed,
                "density": latest.density,
                "congestion_level": latest.congestion_level,
                "updated_at": latest.recorded_at.isoformat() if latest.recorded_at else timestamp,
            })
        else:
            # Fallback to defaults from road profile
            results.append({
                "road_id": road.road_id,
                "road_name": road.road_name,
                "vehicle_count": 80,
                "average_speed": 45.0,
                "density": 1.78,
                "congestion_level": "Low",
                "updated_at": timestamp,
            })

    return {
        "updated_at": timestamp,
        "count": len(results),
        "data": results,
    }


@app.get("/api/v1/traffic/road/{road_id}")
def road_traffic(road_id: str, db: Session = Depends(get_db)):
    """
    Return traffic information for a specific road.
    """
    road = db.query(Road).filter(Road.road_id == road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Road '{road_id}' not found",
        )

    latest = get_latest_reading_for_road(db, road_id)
    timestamp = current_timestamp()

    if latest:
        return {
            "road_id": road.road_id,
            "road_name": road.road_name,
            "vehicle_count": latest.vehicle_count,
            "average_speed": latest.average_speed,
            "density": latest.density,
            "congestion_level": latest.congestion_level,
            "updated_at": latest.recorded_at.isoformat() if latest.recorded_at else timestamp,
        }

    return {
        "road_id": road.road_id,
        "road_name": road.road_name,
        "vehicle_count": 85,
        "average_speed": 40.0,
        "density": 2.12,
        "congestion_level": "Low",
        "updated_at": timestamp,
    }


@app.get("/api/v1/traffic/density")
def traffic_density(db: Session = Depends(get_db)):
    """
    Return aggregated network traffic-density information.
    """
    roads = db.query(Road).all()
    timestamp = current_timestamp()

    total_vehicles = 0
    densities = []
    high_congestion_roads = []

    for road in roads:
        latest = get_latest_reading_for_road(db, road.road_id)
        if latest:
            total_vehicles += latest.vehicle_count
            densities.append(latest.density)
            if latest.congestion_level.lower() in ("high", "severe"):
                high_congestion_roads.append(road.road_id)

    count = len(densities) or 1
    avg_density = sum(densities) / count if densities else 0.0

    return {
        "average_density": round(avg_density, 2),
        "total_vehicle_count": total_vehicles,
        "total_roads": len(roads),
        "total_roads_monitored": len(roads),
        "high_congestion_roads": high_congestion_roads,
        "updated_at": timestamp,
    }


@app.get("/api/v1/traffic/history")
def traffic_history(
    road_id: Optional[str] = Query(None, description="Filter by road ID"),
    start: Optional[str] = Query(None, description="Start timestamp in ISO format"),
    end: Optional[str] = Query(None, description="End timestamp in ISO format"),
    limit: int = Query(100, ge=1, le=1000, description="Max readings to return"),
    db: Session = Depends(get_db),
):
    """
    SRS 7.1: GET /api/v1/traffic/history?road_id={id}&start={ts}&end={ts}
    Returns [ { road_id, timestamp, vehicle_count, density, congestion_level } ]
    """
    query = db.query(TrafficReading)

    if road_id:
        query = query.filter(TrafficReading.road_id == road_id)
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            query = query.filter(TrafficReading.recorded_at >= start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.fromisoformat(end)
            query = query.filter(TrafficReading.recorded_at <= end_dt)
        except ValueError:
            pass

    records = query.order_by(desc(TrafficReading.recorded_at)).limit(limit).all()

    return [
        {
            "road_id": r.road_id,
            "timestamp": r.recorded_at.isoformat() if r.recorded_at else None,
            "vehicle_count": r.vehicle_count,
            "density": r.density,
            "average_speed": r.average_speed,
            "congestion_level": r.congestion_level,
        }
        for r in records
    ]


@app.get("/api/v1/traffic/aggregate")
def traffic_aggregate(
    road_id: Optional[str] = Query(None, description="Filter by road ID"),
    granularity: str = Query("hour", pattern="^(hour|day)$", description="Aggregation granularity (hour or day)"),
    db: Session = Depends(get_db),
):
    """
    SRS 7.1: GET /api/v1/traffic/aggregate?road_id={id}&granularity=hour|day
    Returns rolled-up averages for trend analysis and model features.
    """
    query = db.query(TrafficReading)
    if road_id:
        query = query.filter(TrafficReading.road_id == road_id)

    readings = query.order_by(TrafficReading.recorded_at.asc()).all()
    if not readings:
        return []

    buckets = defaultdict(lambda: {"counts": [], "densities": [], "speeds": [], "levels": []})

    for r in readings:
        dt = r.recorded_at
        key_road = r.road_id
        if granularity == "hour":
            bucket_key = f"{key_road}_{dt.hour:02d}:00"
            label = f"{dt.hour:02d}:00"
        else:
            bucket_key = f"{key_road}_{dt.strftime('%Y-%m-%d')}"
            label = dt.strftime("%Y-%m-%d")

        b = buckets[(key_road, label)]
        b["counts"].append(r.vehicle_count)
        b["densities"].append(r.density)
        b["speeds"].append(r.average_speed)
        b["levels"].append(r.congestion_level)

    aggregated = []
    for (r_id, label), data in sorted(buckets.items()):
        n = len(data["counts"])
        avg_count = round(sum(data["counts"]) / n, 1)
        avg_density = round(sum(data["densities"]) / n, 2)
        avg_speed = round(sum(data["speeds"]) / n, 1)
        # Dominant congestion level
        dominant_level = max(set(data["levels"]), key=data["levels"].count)

        aggregated.append({
            "road_id": r_id,
            "bucket": label,
            "avg_vehicle_count": avg_count,
            "avg_density": avg_density,
            "avg_speed": avg_speed,
            "dominant_congestion_level": dominant_level,
            "sample_count": n,
        })

    return aggregated


@app.get("/api/v1/traffic/road-condition/{road_id}")
def road_condition(road_id: str, db: Session = Depends(get_db)):
    """
    SRS 7.1: GET /api/v1/traffic/road-condition/{road_id}
    Returns { road_id, status, notes, updated_at } (closures, construction, hazards)
    """
    condition = db.query(RoadCondition).filter(RoadCondition.road_id == road_id).first()
    road = db.query(Road).filter(Road.road_id == road_id).first()

    if not road and not condition:
        raise HTTPException(
            status_code=404,
            detail=f"Road '{road_id}' not found",
        )

    latest = get_latest_reading_for_road(db, road_id)
    timestamp = current_timestamp()

    status = condition.status if condition else (latest.congestion_level if latest else "CLEAR")
    notes = condition.notes if condition else "Normal operations"
    updated_at = condition.updated_at.isoformat() if condition and condition.updated_at else timestamp

    return {
        "road_id": road_id,
        "road_name": road.road_name if road else road_id,
        "status": status,
        "notes": notes,
        "vehicle_count": latest.vehicle_count if latest else 85,
        "average_speed": latest.average_speed if latest else 40.0,
        "density": latest.density if latest else 2.12,
        "updated_at": updated_at,
    }