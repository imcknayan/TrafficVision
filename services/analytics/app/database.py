import os
from pathlib import Path
from sqlalchemy import create_engine, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT_DIR / "trafficvision.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class Road(Base):
    __tablename__ = "roads"

    road_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    road_name: Mapped[str] = mapped_column(String(255), nullable=False)
    road_capacity: Mapped[int] = mapped_column(Integer, nullable=True)


class TrafficReading(Base):
    __tablename__ = "traffic_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    road_id: Mapped[str] = mapped_column(String(64), ForeignKey("roads.road_id"), nullable=False, index=True)
    recorded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    vehicle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_speed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    congestion_level: Mapped[str] = mapped_column(String(32), nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
