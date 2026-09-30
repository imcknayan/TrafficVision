import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.orm import Session

try:
    from app.database import Base, Road, TrafficReading, RoadCondition, engine, SessionLocal
except (ImportError, AttributeError, ModuleNotFoundError):
    import importlib.util
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

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CSV_PATH = DATA_DIR / "historical_traffic.csv"

ROADS_DATA = [
    {"road_id": "R001", "road_name": "Main Expressway", "road_capacity": 300, "base_speed": 60, "base_volume": 120, "condition_status": "CLEAR", "notes": "Optimal conditions, normal flow"},
    {"road_id": "R002", "road_name": "Central Avenue / Downtown Grid", "road_capacity": 250, "base_speed": 45, "base_volume": 140, "condition_status": "CLEAR", "notes": "Downtown area, normal signals"},
    {"road_id": "R003", "road_name": "West Ring Road", "road_capacity": 250, "base_speed": 50, "base_volume": 130, "condition_status": "MODERATE", "notes": "Slow moving traffic near junction"},
    {"road_id": "R004", "road_name": "North Boulevard", "road_capacity": 200, "base_speed": 65, "base_volume": 60, "condition_status": "CLEAR", "notes": "Free flowing corridor"},
    {"road_id": "R005", "road_name": "Industrial Highway", "road_capacity": 250, "base_speed": 40, "base_volume": 150, "condition_status": "CONSTRUCTION", "notes": "Right lane closure for repaving, speed reduced"},
    {"road_id": "R006", "road_name": "Airport Corridor", "road_capacity": 300, "base_speed": 35, "base_volume": 210, "condition_status": "CONGESTED", "notes": "Heavy airport departure traffic"},
    {"road_id": "R007", "road_name": "Harbor Tunnel Approach", "road_capacity": 350, "base_speed": 25, "base_volume": 260, "condition_status": "HAZARD", "notes": "Tunnel maintenance, lane 2 closed"},
    {"road_id": "road-001", "road_name": "Main Road", "road_capacity": 200, "base_speed": 45, "base_volume": 85, "condition_status": "low", "notes": "Normal flow"},
    {"road_id": "road-002", "road_name": "Market Road", "road_capacity": 250, "base_speed": 30, "base_volume": 165, "condition_status": "medium", "notes": "Market activity causing minor delays"},
    {"road_id": "road-003", "road_name": "Highway Road", "road_capacity": 350, "base_speed": 20, "base_volume": 240, "condition_status": "high", "notes": "Highway volume high near junction"},
    {"road_id": "road-004", "road_name": "College Road", "road_capacity": 200, "base_speed": 35, "base_volume": 120, "condition_status": "medium", "notes": "College rush hours"},
]


def classify_level(density: float) -> str:
    if density >= 28.0:
        return "Severe"
    if density >= 20.0:
        return "High"
    if density >= 10.0:
        return "Medium"
    return "Low"


def generate_readings(days: int = 28):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = now - timedelta(days=days)
    readings = []

    # Deterministic seed for reproducible evaluation
    rng = random.Random(42)

    total_hours = days * 24
    for h in range(total_hours + 1):
        ts = start_time + timedelta(hours=h)
        hour = ts.hour
        weekday = ts.weekday()
        is_weekend = weekday >= 5

        # Hourly demand multipliers
        if is_weekend:
            # Weekend peak around 11:00-16:00
            hour_factor = 0.35 + 0.65 * math.exp(-((hour - 14) ** 2) / 18.0)
        else:
            # Weekday dual peaks: 08:30 and 18:00
            morning_peak = math.exp(-((hour - 8.5) ** 2) / 3.0)
            evening_peak = math.exp(-((hour - 18.0) ** 2) / 4.0)
            midday_base = 0.45 if 10 <= hour <= 15 else 0.2
            hour_factor = max(0.15, midday_base + 0.85 * morning_peak + 0.95 * evening_peak)

        for road in ROADS_DATA:
            road_id = road["road_id"]
            base_vol = road["base_volume"]
            base_spd = road["base_speed"]

            noise = rng.uniform(0.9, 1.1)
            volume = int(base_vol * hour_factor * noise)
            volume = max(5, volume)

            # Speed drops as volume approaches capacity
            congestion_ratio = min(1.2, volume / road["road_capacity"])
            speed = max(8.0, base_spd * (1.0 - 0.7 * (congestion_ratio ** 1.5)) * rng.uniform(0.92, 1.08))
            speed = round(speed, 1)

            density = round(volume / max(speed, 5.0), 2)
            level = classify_level(density)

            readings.append({
                "road_id": road_id,
                "recorded_at": ts.isoformat(),
                "vehicle_count": volume,
                "average_speed": speed,
                "density": density,
                "congestion_level": level,
            })

    return readings


def save_dataset_csv(readings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["road_id", "recorded_at", "vehicle_count", "average_speed", "density", "congestion_level"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(readings)
    print(f"Saved {len(readings)} historical readings to {CSV_PATH}")


def seed_database(db: Session, readings=None):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # 1. Seed Roads
    for r in ROADS_DATA:
        existing_road = db.query(Road).filter(Road.road_id == r["road_id"]).first()
        if not existing_road:
            road_obj = Road(
                road_id=r["road_id"],
                road_name=r["road_name"],
                road_capacity=r["road_capacity"],
            )
            db.add(road_obj)
    db.commit()

    # 2. Seed Road Conditions
    for r in ROADS_DATA:
        existing_cond = db.query(RoadCondition).filter(RoadCondition.road_id == r["road_id"]).first()
        if not existing_cond:
            cond_obj = RoadCondition(
                road_id=r["road_id"],
                status=r["condition_status"],
                notes=r["notes"],
                updated_at=datetime.now(timezone.utc),
            )
            db.add(cond_obj)
        else:
            existing_cond.status = r["condition_status"]
            existing_cond.notes = r["notes"]
            existing_cond.updated_at = datetime.now(timezone.utc)
    db.commit()

    # 3. Seed Traffic Readings if empty
    existing_count = db.query(TrafficReading).count()
    if existing_count == 0:
        if readings is None:
            readings = generate_readings(days=28)
        
        objects = [
            TrafficReading(
                road_id=row["road_id"],
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
                vehicle_count=row["vehicle_count"],
                average_speed=row["average_speed"],
                density=row["density"],
                congestion_level=row["congestion_level"],
            )
            for row in readings
        ]
        # Batch insert
        db.bulk_save_objects(objects)
        db.commit()
        print(f"Seeded {len(objects)} traffic readings into the database.")
    else:
        print(f"Database already has {existing_count} traffic readings.")


if __name__ == "__main__":
    readings = generate_readings(days=28)
    save_dataset_csv(readings)
    with SessionLocal() as db:
        seed_database(db, readings)
