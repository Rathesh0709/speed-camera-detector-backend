-- PostgreSQL + PostGIS Database Schema for Navigation App
-- PostgreSQL 15+ with PostGIS extension required

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SPEED CAMERAS TABLE (Point Geometry)
-- ============================================
CREATE TABLE speed_cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    speed_limit_kmh INTEGER NOT NULL,
    camera_type VARCHAR(50) NOT NULL, -- 'fixed', 'mobile', 'average_speed'
    direction_degrees INTEGER, -- 0-360, NULL if omnidirectional
    verified BOOLEAN DEFAULT FALSE,
    verification_count INTEGER DEFAULT 0,
    confidence_score DECIMAL(3, 2) DEFAULT 0.50 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    reported_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================
-- ROAD SPEED LIMITS TABLE (LineString Geometry)
-- ============================================
CREATE TABLE road_speed_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    road_segment GEOGRAPHY(LINESTRING, 4326) NOT NULL,
    speed_limit_kmh INTEGER NOT NULL,
    road_name VARCHAR(255),
    road_type VARCHAR(50), -- 'highway', 'urban', 'rural', 'residential'
    direction VARCHAR(20), -- 'forward', 'backward', 'both'
    verified BOOLEAN DEFAULT FALSE,
    verification_count INTEGER DEFAULT 0,
    confidence_score DECIMAL(3, 2) DEFAULT 0.50 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    reported_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================
-- HAZARD DETECTIONS TABLE (Point Geometry)
-- ============================================
CREATE TABLE hazard_detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    hazard_type VARCHAR(50) NOT NULL, -- 'pothole', 'debris', 'accident', 'construction', 'weather', 'animal'
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    confidence_score DECIMAL(3, 2) DEFAULT 0.50 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    detected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE, -- NULL for permanent hazards
    verified BOOLEAN DEFAULT FALSE,
    verification_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    image_url TEXT
);

-- ============================================
-- USER CAMERA REPORTS TABLE
-- ============================================
CREATE TABLE user_camera_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    camera_id UUID NOT NULL REFERENCES speed_cameras(id) ON DELETE CASCADE,
    report_type VARCHAR(20) NOT NULL, -- 'confirm', 'dispute', 'update_speed', 'remove'
    reported_location GEOGRAPHY(POINT, 4326),
    reported_speed_limit_kmh INTEGER,
    confidence_score DECIMAL(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, camera_id, report_type, created_at)
);

-- ============================================
-- USER SPEED LIMIT REPORTS TABLE
-- ============================================
CREATE TABLE user_speed_limit_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    speed_limit_id UUID NOT NULL REFERENCES road_speed_limits(id) ON DELETE CASCADE,
    report_type VARCHAR(20) NOT NULL, -- 'confirm', 'dispute', 'update_speed', 'update_segment'
    reported_segment GEOGRAPHY(LINESTRING, 4326),
    reported_speed_limit_kmh INTEGER,
    confidence_score DECIMAL(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, speed_limit_id, report_type, created_at)
);

-- ============================================
-- INDEXES
-- ============================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);

-- Speed cameras indexes (GiST for spatial queries)
CREATE INDEX idx_speed_cameras_location ON speed_cameras USING GIST(location);
CREATE INDEX idx_speed_cameras_verified ON speed_cameras(verified);
CREATE INDEX idx_speed_cameras_confidence ON speed_cameras(confidence_score);
CREATE INDEX idx_speed_cameras_type ON speed_cameras(camera_type);
CREATE INDEX idx_speed_cameras_reported_by ON speed_cameras(reported_by);

-- Road speed limits indexes (GiST for spatial queries)
CREATE INDEX idx_road_speed_limits_segment ON road_speed_limits USING GIST(road_segment);
CREATE INDEX idx_road_speed_limits_verified ON road_speed_limits(verified);
CREATE INDEX idx_road_speed_limits_confidence ON road_speed_limits(confidence_score);
CREATE INDEX idx_road_speed_limits_road_name ON road_speed_limits(road_name);
CREATE INDEX idx_road_speed_limits_reported_by ON road_speed_limits(reported_by);

-- Hazard detections indexes (GiST for spatial queries)
CREATE INDEX idx_hazard_detections_location ON hazard_detections USING GIST(location);
CREATE INDEX idx_hazard_detections_type ON hazard_detections(hazard_type);
CREATE INDEX idx_hazard_detections_severity ON hazard_detections(severity);
CREATE INDEX idx_hazard_detections_active ON hazard_detections(is_active);
CREATE INDEX idx_hazard_detections_detected_at ON hazard_detections(detected_at);
CREATE INDEX idx_hazard_detections_expires_at ON hazard_detections(expires_at);
CREATE INDEX idx_hazard_detections_verified ON hazard_detections(verified);
CREATE INDEX idx_hazard_detections_detected_by ON hazard_detections(detected_by);

-- User reports indexes
CREATE INDEX idx_user_camera_reports_user ON user_camera_reports(user_id);
CREATE INDEX idx_user_camera_reports_camera ON user_camera_reports(camera_id);
CREATE INDEX idx_user_camera_reports_created_at ON user_camera_reports(created_at);

CREATE INDEX idx_user_speed_limit_reports_user ON user_speed_limit_reports(user_id);
CREATE INDEX idx_user_speed_limit_reports_speed_limit ON user_speed_limit_reports(speed_limit_id);
CREATE INDEX idx_user_speed_limit_reports_created_at ON user_speed_limit_reports(created_at);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_speed_cameras_updated_at BEFORE UPDATE ON speed_cameras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_road_speed_limits_updated_at BEFORE UPDATE ON road_speed_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to auto-verify cameras/speed limits after threshold reports
CREATE OR REPLACE FUNCTION check_verification_threshold()
RETURNS TRIGGER AS $$
DECLARE
    confirm_count INTEGER;
    total_count INTEGER;
BEGIN
    -- Count confirmations for the camera/speed limit
    IF TG_TABLE_NAME = 'user_camera_reports' THEN
        SELECT COUNT(*) INTO confirm_count
        FROM user_camera_reports
        WHERE camera_id = NEW.camera_id AND report_type = 'confirm';
        
        SELECT COUNT(*) INTO total_count
        FROM user_camera_reports
        WHERE camera_id = NEW.camera_id;
        
        -- Auto-verify if 5+ confirmations and 80%+ are confirmations
        IF confirm_count >= 5 AND (confirm_count::DECIMAL / NULLIF(total_count, 0)) >= 0.8 THEN
            UPDATE speed_cameras
            SET verified = TRUE, verification_count = confirm_count
            WHERE id = NEW.camera_id;
        END IF;
    ELSIF TG_TABLE_NAME = 'user_speed_limit_reports' THEN
        SELECT COUNT(*) INTO confirm_count
        FROM user_speed_limit_reports
        WHERE speed_limit_id = NEW.speed_limit_id AND report_type = 'confirm';
        
        SELECT COUNT(*) INTO total_count
        FROM user_speed_limit_reports
        WHERE speed_limit_id = NEW.speed_limit_id;
        
        -- Auto-verify if 5+ confirmations and 80%+ are confirmations
        IF confirm_count >= 5 AND (confirm_count::DECIMAL / NULLIF(total_count, 0)) >= 0.8 THEN
            UPDATE road_speed_limits
            SET verified = TRUE, verification_count = confirm_count
            WHERE id = NEW.speed_limit_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER check_camera_verification AFTER INSERT ON user_camera_reports
    FOR EACH ROW EXECUTE FUNCTION check_verification_threshold();

CREATE TRIGGER check_speed_limit_verification AFTER INSERT ON user_speed_limit_reports
    FOR EACH ROW EXECUTE FUNCTION check_verification_threshold();

-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE users IS 'User accounts for the navigation app';
COMMENT ON TABLE speed_cameras IS 'Speed camera locations with point geometry';
COMMENT ON TABLE road_speed_limits IS 'Road speed limit segments with linestring geometry';
COMMENT ON TABLE hazard_detections IS 'Hazard detections with point geometry and expiration';
COMMENT ON TABLE user_camera_reports IS 'User reports/confirmations for speed cameras';
COMMENT ON TABLE user_speed_limit_reports IS 'User reports/confirmations for road speed limits';

COMMENT ON COLUMN speed_cameras.location IS 'Point geometry in WGS84 (SRID 4326)';
COMMENT ON COLUMN road_speed_limits.road_segment IS 'LineString geometry in WGS84 (SRID 4326)';
COMMENT ON COLUMN hazard_detections.location IS 'Point geometry in WGS84 (SRID 4326)';
COMMENT ON COLUMN speed_cameras.confidence_score IS 'Confidence score from 0.0 to 1.0';
COMMENT ON COLUMN road_speed_limits.confidence_score IS 'Confidence score from 0.0 to 1.0';
COMMENT ON COLUMN hazard_detections.confidence_score IS 'Confidence score from 0.0 to 1.0';
