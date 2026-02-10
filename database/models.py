"""
SQLAlchemy async models for Navigation App database.
Requires: sqlalchemy[asyncio], asyncpg, geoalchemy2
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User accounts for the navigation app."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    trips_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    camera_reports = relationship("UserCameraReport", back_populates="user")
    speed_limit_reports = relationship("UserSpeedLimitReport", back_populates="user")
    reported_cameras = relationship("SpeedCamera", back_populates="reporter")
    reported_speed_limits = relationship("RoadSpeedLimit", back_populates="reporter")
    detected_hazards = relationship("HazardDetection", back_populates="detector")
    reported_hazard_segments = relationship("HazardousRoadSegment", back_populates="reporter")
    hazard_reports = relationship("HazardReport", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class SpeedCamera(Base):
    """Speed camera locations with point geometry."""

    __tablename__ = "speed_cameras"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    speed_limit_kmh = Column(Integer, nullable=False)
    camera_type = Column(String(50), nullable=False, index=True)
    direction_degrees = Column(Integer, nullable=True)  # 0-360, NULL if omnidirectional
    verified = Column(Boolean, default=False, index=True)
    verification_count = Column(Integer, default=0)
    confidence_score = Column(
        Numeric(3, 2),
        default=0.50,
        index=True,
    )
    reported_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    notes = Column(Text, nullable=True)

    # Relationships
    reporter = relationship("User", back_populates="reported_cameras")
    user_reports = relationship("UserCameraReport", back_populates="camera")
    
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="speed_cameras_confidence_check"),
    )

    def __repr__(self):
        return f"<SpeedCamera(id={self.id}, type={self.camera_type}, speed_limit={self.speed_limit_kmh}kmh)>"


class RoadSpeedLimit(Base):
    """Road speed limit segments with linestring geometry."""

    __tablename__ = "road_speed_limits"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    road_segment = Column(
        Geography(geometry_type="LINESTRING", srid=4326), nullable=False, index=True
    )
    speed_limit_kmh = Column(Integer, nullable=False)
    road_name = Column(String(255), nullable=True, index=True)
    road_type = Column(String(50), nullable=True)
    direction = Column(String(20), nullable=True)  # 'forward', 'backward', 'both'
    verified = Column(Boolean, default=False, index=True)
    verification_count = Column(Integer, default=0)
    confidence_score = Column(
        Numeric(3, 2),
        default=0.50,
        index=True,
    )
    reported_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    notes = Column(Text, nullable=True)

    # Relationships
    reporter = relationship("User", back_populates="reported_speed_limits")
    user_reports = relationship("UserSpeedLimitReport", back_populates="speed_limit")
    
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="road_speed_limits_confidence_check"),
    )

    def __repr__(self):
        return f"<RoadSpeedLimit(id={self.id}, speed_limit={self.speed_limit_kmh}kmh, road={self.road_name})>"


class HazardDetection(Base):
    """Hazard detections with point geometry and expiration."""

    __tablename__ = "hazard_detections"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    hazard_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    confidence_score = Column(
        Numeric(3, 2),
        default=0.50,
    )
    detected_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detected_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    verified = Column(Boolean, default=False, index=True)
    verification_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)

    # Relationships
    detector = relationship("User", back_populates="detected_hazards")
    
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="hazard_detections_confidence_check"),
    )

    def __repr__(self):
        return f"<HazardDetection(id={self.id}, type={self.hazard_type}, severity={self.severity})>"


class UserCameraReport(Base):
    """User reports/confirmations for speed cameras."""

    __tablename__ = "user_camera_reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    camera_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("speed_cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type = Column(String(20), nullable=False)
    reported_location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    reported_speed_limit_kmh = Column(Integer, nullable=True)
    confidence_score = Column(
        Numeric(3, 2),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="camera_reports")
    camera = relationship("SpeedCamera", back_populates="user_reports")

    # Unique constraint to prevent duplicate reports
    __table_args__ = (
        UniqueConstraint(
            "user_id", "camera_id", "report_type", "created_at", name="uq_user_camera_report"
        ),
        CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)", name="user_camera_reports_confidence_check"),
    )

    def __repr__(self):
        return f"<UserCameraReport(id={self.id}, user_id={self.user_id}, camera_id={self.camera_id}, type={self.report_type})>"


class UserSpeedLimitReport(Base):
    """User reports/confirmations for road speed limits."""

    __tablename__ = "user_speed_limit_reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speed_limit_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("road_speed_limits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type = Column(String(20), nullable=False)
    reported_segment = Column(
        Geography(geometry_type="LINESTRING", srid=4326), nullable=True
    )
    reported_speed_limit_kmh = Column(Integer, nullable=True)
    confidence_score = Column(
        Numeric(3, 2),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="speed_limit_reports")
    speed_limit = relationship("RoadSpeedLimit", back_populates="user_reports")

    # Unique constraint to prevent duplicate reports
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "speed_limit_id",
            "report_type",
            "created_at",
            name="uq_user_speed_limit_report",
        ),
        CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)", name="user_speed_limit_reports_confidence_check"),
    )

    def __repr__(self):
        return f"<UserSpeedLimitReport(id={self.id}, user_id={self.user_id}, speed_limit_id={self.speed_limit_id}, type={self.report_type})>"


class SchoolZone(Base):
    """School zone locations with point geometry."""

    __tablename__ = "school_zones"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    name = Column(String(255), nullable=True, index=True)
    address = Column(Text, nullable=True)
    osm_id = Column(String(50), nullable=True, unique=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<SchoolZone(id={self.id}, name={self.name})>"


class HospitalZone(Base):
    """Hospital zone locations with point geometry."""

    __tablename__ = "hospital_zones"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    name = Column(String(255), nullable=True, index=True)
    address = Column(Text, nullable=True)
    osm_id = Column(String(50), nullable=True, unique=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<HospitalZone(id={self.id}, name={self.name})>"
class HazardousRoadSegment(Base):
    """Hazardous road segments with linestring geometry."""

    __tablename__ = "hazardous_road_segments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    road_segment = Column(
        Geography(geometry_type="LINESTRING", srid=4326), nullable=False, index=True
    )
    hazard_type = Column(String(100), nullable=False, index=True)  # e.g., 'potholes', 'rough_road', 'flooded'
    severity = Column(String(20), default="medium", index=True)
    road_name = Column(String(255), nullable=True, index=True)
    osm_id = Column(String(50), nullable=True, unique=True)
    confidence_score = Column(
        Numeric(3, 2),
        default=0.50,
        index=True,
    )
    reported_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    notes = Column(Text, nullable=True)

    # Relationships
    reporter = relationship("User", back_populates="reported_hazard_segments")

    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="hazardous_road_segments_confidence_check"),
    )

    def __repr__(self):
        return f"<HazardousRoadSegment(id={self.id}, type={self.hazard_type}, road={self.road_name})>"


class HazardReport(Base):
    """Generic user reports for hazards or camera zones with reasons."""

    __tablename__ = "hazard_reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location = Column(
        Geography(geometry_type="GEOMETRY", srid=4326), nullable=False, index=True
    )
    report_type = Column(String(50), nullable=False, index=True)  # 'camera_zone', 'hazard_point', 'hazard_road'
    reason = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="hazard_reports")

    def __repr__(self):
        return f"<HazardReport(id={self.id}, user_id={self.user_id}, type={self.report_type})>"
