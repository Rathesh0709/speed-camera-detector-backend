"""
Database package for Navigation App.
PostgreSQL + PostGIS with async SQLAlchemy.
"""

from .database import (
    AsyncSessionLocal,
    check_db_health,
    close_db,
    get_db,
    init_db,
)
from .models import (
    HazardDetection,
    RoadSpeedLimit,
    SpeedCamera,
    User,
    UserCameraReport,
    UserSpeedLimitReport,
)
from .queries import (
    create_road_speed_limit,
    create_speed_camera,
    get_nearby_hazards,
    get_nearby_speed_cameras,
    get_nearby_speed_limits,
    get_speed_cameras_along_route,
    get_speed_limits_along_route,
)

__all__ = [
    # Database connection
    "get_db",
    "init_db",
    "close_db",
    "check_db_health",
    "AsyncSessionLocal",
    # Models
    "User",
    "SpeedCamera",
    "RoadSpeedLimit",
    "HazardDetection",
    "UserCameraReport",
    "UserSpeedLimitReport",
    # Query functions
    "get_nearby_speed_cameras",
    "get_nearby_speed_limits",
    "get_nearby_hazards",
    "get_speed_cameras_along_route",
    "get_speed_limits_along_route",
    "create_speed_camera",
    "create_road_speed_limit",
]
