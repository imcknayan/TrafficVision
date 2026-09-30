import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

from pathlib import Path

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
    road_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    readings = relationship("TrafficReading", back_populates="road", cascade="all, delete-orphan")
    condition = relationship("RoadCondition", back_populates="road", uselist=False, cascade="all, delete-orphan")


class TrafficReading(Base):
    __tablename__ = "traffic_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    road_id: Mapped[str] = mapped_column(String(64), ForeignKey("roads.road_id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    vehicle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_speed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    congestion_level: Mapped[str] = mapped_column(String(32), nullable=False)

    road = relationship("Road", back_populates="readings")

    __table_args__ = (
        Index("idx_traffic_road_time", "road_id", "recorded_at"),
        Index("idx_traffic_time", "recorded_at"),
    )


class RoadCondition(Base):
    __tablename__ = "road_conditions"

    road_id: Mapped[str] = mapped_column(String(64), ForeignKey("roads.road_id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    road = relationship("Road", back_populates="condition")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
