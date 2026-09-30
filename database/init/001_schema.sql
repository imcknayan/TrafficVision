-- Milestone 1 shared PostgreSQL schema. Traffic tables are owned by Intern 2.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'traffic_operator', 'public')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_jti UUID NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Traffic monitoring tables for Milestone 2
CREATE TABLE IF NOT EXISTS roads (
    road_id VARCHAR(64) PRIMARY KEY,
    road_name VARCHAR(255) NOT NULL,
    road_capacity INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS traffic_readings (
    id BIGSERIAL PRIMARY KEY,
    road_id VARCHAR(64) NOT NULL REFERENCES roads(road_id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_count INTEGER NOT NULL DEFAULT 0,
    average_speed DOUBLE PRECISION NOT NULL DEFAULT 0,
    density DOUBLE PRECISION NOT NULL DEFAULT 0,
    congestion_level VARCHAR(32) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_traffic_road_time
ON traffic_readings(road_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_traffic_time
ON traffic_readings(recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_traffic_road_time_level
ON traffic_readings(road_id, recorded_at DESC, congestion_level);

CREATE TABLE IF NOT EXISTS road_conditions (
    road_id VARCHAR(64) PRIMARY KEY REFERENCES roads(road_id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Alerts table for Milestone 3
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(64) PRIMARY KEY,
    type VARCHAR(32) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    road_id VARCHAR(64) REFERENCES roads(road_id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_road_created ON alerts(road_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_read ON alerts(is_read);

