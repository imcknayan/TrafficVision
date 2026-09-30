import io
import csv
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

try:
    from app.database import get_db, Road, TrafficReading
except (ImportError, AttributeError, ModuleNotFoundError):
    import importlib.util
    from pathlib import Path
    _db_path = Path(__file__).resolve().parent / "database.py"
    _spec = importlib.util.spec_from_file_location("analytics_database", _db_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    get_db = _mod.get_db
    Road = _mod.Road
    TrafficReading = _mod.TrafficReading

app = FastAPI(
    title="TrafficVision AI Analytics Service",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONGESTION_WEIGHTS = {
    "low": 0.15,
    "medium": 0.45,
    "high": 0.75,
    "severe": 0.95,
}

PRIMARY_ROADS = ["R001", "R002", "R003", "R004", "R005", "R006", "R007"]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "analytics",
    }


@app.get("/api/v1/analytics/trends")
def traffic_trends(
    road_id: str = Query("R001", description="Monitored Road ID"),
    range_param: str = Query("day", alias="range", pattern="^(day|week|month)$", description="Trend range: day or week"),
    db: Session = Depends(get_db),
):
    """
    SRS 7.2: GET /api/v1/analytics/trends?road_id={id}&range=day|week
    Returns { road_id, points: [ { period, avg_congestion } ] }
    """
    readings = (
        db.query(TrafficReading)
        .filter(TrafficReading.road_id == road_id)
        .order_by(TrafficReading.recorded_at.asc())
        .all()
    )

    if not readings:
        # Fallback default hourly curve
        points = []
        for h in range(24):
            cong = 0.8 if (8 <= h <= 10 or 17 <= h <= 20) else 0.2
            points.append({
                "period": f"{h:02d}:00",
                "avg_congestion": cong,
                "avg_speed": 35.0,
                "avg_density": cong * 25.0,
                "sample_count": 1,
            })
        return {"road_id": road_id, "range": range_param, "points": points}

    buckets = defaultdict(lambda: {"cong_scores": [], "speeds": [], "densities": []})

    for r in readings:
        dt = r.recorded_at
        if range_param == "week":
            period = dt.strftime("%A")  # Monday, Tuesday, ...
        else:
            period = f"{dt.hour:02d}:00"

        c_level = r.congestion_level.lower()
        score = CONGESTION_WEIGHTS.get(c_level, 0.20)
        buckets[period]["cong_scores"].append(score)
        buckets[period]["speeds"].append(r.average_speed)
        buckets[period]["densities"].append(r.density)

    points = []
    if range_param == "week":
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for p in order:
            if p in buckets:
                b = buckets[p]
                n = len(b["cong_scores"])
                points.append({
                    "period": p,
                    "avg_congestion": round(sum(b["cong_scores"]) / n, 2),
                    "avg_speed": round(sum(b["speeds"]) / n, 1),
                    "avg_density": round(sum(b["densities"]) / n, 2),
                    "sample_count": n,
                })
    else:
        for h in range(24):
            p = f"{h:02d}:00"
            if p in buckets:
                b = buckets[p]
                n = len(b["cong_scores"])
                points.append({
                    "period": p,
                    "avg_congestion": round(sum(b["cong_scores"]) / n, 2),
                    "avg_speed": round(sum(b["speeds"]) / n, 1),
                    "avg_density": round(sum(b["densities"]) / n, 2),
                    "sample_count": n,
                })

    return {
        "road_id": road_id,
        "range": range_param,
        "points": points,
    }


@app.get("/api/v1/analytics/heatmap")
def traffic_heatmap(
    range_param: str = Query("day", alias="range", pattern="^(day|week)$", description="Heatmap temporal range"),
    db: Session = Depends(get_db),
):
    """
    SRS 7.2: GET /api/v1/analytics/heatmap?range={range}
    Returns { roads: [...], time_buckets: [...], values: [][] }
    """
    roads = [r.road_id for r in db.query(Road).filter(Road.road_id.in_(PRIMARY_ROADS)).all()]
    if not roads:
        roads = PRIMARY_ROADS

    time_buckets = [f"{h:02d}:00" for h in range(24)]
    values = []

    # Preload all readings for performance
    readings = db.query(TrafficReading).filter(TrafficReading.road_id.in_(roads)).all()
    matrix = defaultdict(lambda: defaultdict(list))

    for r in readings:
        h_str = f"{r.recorded_at.hour:02d}:00"
        score = CONGESTION_WEIGHTS.get(r.congestion_level.lower(), 0.15)
        matrix[r.road_id][h_str].append(score)

    for r_id in roads:
        road_row = []
        for tb in time_buckets:
            scores = matrix[r_id].get(tb, [])
            if scores:
                avg_score = round(sum(scores) / len(scores), 2)
            else:
                # Deterministic approximation if no reading for bucket
                h_int = int(tb.split(":")[0])
                avg_score = 0.75 if (8 <= h_int <= 10 or 17 <= h_int <= 20) else 0.15
            road_row.append(avg_score)
        values.append(road_row)

    return {
        "roads": roads,
        "time_buckets": time_buckets,
        "values": values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/analytics/reports")
def traffic_reports(
    range: str = Query("week", pattern="^(day|week|month)$"),
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
):
    """
    SRS 7.2: GET /api/v1/analytics/reports?range={range}&format=csv
    Returns downloadable historical report data.
    """
    readings = (
        db.query(TrafficReading)
        .order_by(desc(TrafficReading.recorded_at))
        .limit(500)
        .all()
    )

    data = [
        {
            "id": r.id,
            "road_id": r.road_id,
            "timestamp": r.recorded_at.isoformat() if r.recorded_at else "",
            "vehicle_count": r.vehicle_count,
            "average_speed_kmph": r.average_speed,
            "density": r.density,
            "congestion_level": r.congestion_level,
        }
        for r in readings
    ]

    if format == "json":
        return {
            "range": range,
            "record_count": len(data),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

    # Generate CSV response
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    else:
        output.write("id,road_id,timestamp,vehicle_count,average_speed_kmph,density,congestion_level\n")

    csv_content = output.getvalue()
    filename = f"traffic_report_{range}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
