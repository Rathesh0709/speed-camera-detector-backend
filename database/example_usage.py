"""
Example FastAPI endpoints showing how to use the database models and queries.
This is a reference file - integrate these patterns into your FastAPI app.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import SpeedCamera, RoadSpeedLimit, HazardDetection
from .queries import (
    get_nearby_speed_cameras,
    get_nearby_speed_limits,
    get_nearby_hazards,
    create_speed_camera,
    create_road_speed_limit,
)

router = APIRouter(prefix="/api/v1", tags=["navigation"])


# ============================================
# Pydantic Models for Request/Response
# ============================================

class SpeedCameraResponse(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    speed_limit_kmh: int
    camera_type: str
    direction_degrees: int | None
    verified: bool
    confidence_score: float

    class Config:
        from_attributes = True


class RoadSpeedLimitResponse(BaseModel):
    id: UUID
    speed_limit_kmh: int
    road_name: str | None
    road_type: str | None
    verified: bool
    confidence_score: float

    class Config:
        from_attributes = True


class HazardResponse(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    hazard_type: str
    severity: str
    confidence_score: float
    is_active: bool

    class Config:
        from_attributes = True


class CreateSpeedCameraRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_limit_kmh: int = Field(..., gt=0, le=200)
    camera_type: str = Field(..., pattern="^(fixed|mobile|average_speed)$")
    direction_degrees: int | None = Field(None, ge=0, le=360)
    confidence_score: float = Field(0.50, ge=0.0, le=1.0)
    notes: str | None = None


# ============================================
# Example Endpoints
# ============================================

@router.get("/cameras/nearby", response_model=List[SpeedCameraResponse])
async def get_cameras_nearby(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_meters: float = Query(1000.0, gt=0, le=10000, description="Search radius in meters"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    verified_only: bool = Query(False, description="Only return verified cameras"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get speed cameras near a location.
    """
    cameras = await get_nearby_speed_cameras(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        min_confidence=min_confidence,
        verified_only=verified_only,
    )
    
    # Convert to response format
    # Note: You'll need to extract lat/lon from the PostGIS geometry
    # This is a simplified example - you may want to add a helper function
    return cameras


@router.get("/speed-limits/nearby", response_model=List[RoadSpeedLimitResponse])
async def get_speed_limits_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(500.0, gt=0, le=5000),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    verified_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Get road speed limits near a location.
    """
    speed_limits = await get_nearby_speed_limits(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        min_confidence=min_confidence,
        verified_only=verified_only,
    )
    return speed_limits


@router.get("/hazards/nearby", response_model=List[HazardResponse])
async def get_hazards_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(1000.0, gt=0, le=10000),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get active hazards near a location.
    """
    hazards = await get_nearby_hazards(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        min_confidence=min_confidence,
        active_only=active_only,
    )
    return hazards


@router.post("/cameras", response_model=SpeedCameraResponse, status_code=201)
async def create_camera(
    request: CreateSpeedCameraRequest,
    # In production, get user_id from JWT token
    # user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new speed camera report.
    """
    camera = await create_speed_camera(
        db=db,
        latitude=request.latitude,
        longitude=request.longitude,
        speed_limit_kmh=request.speed_limit_kmh,
        camera_type=request.camera_type,
        direction_degrees=request.direction_degrees,
        confidence_score=request.confidence_score,
        # reported_by=user_id,  # Uncomment when auth is implemented
        notes=request.notes,
    )
    await db.commit()
    return camera


# ============================================
# Example FastAPI App Setup
# ============================================

"""
# In your main FastAPI app (e.g., main.py):

from fastapi import FastAPI
from database import init_db, close_db
from database.example_usage import router as navigation_router

app = FastAPI(title="Navigation App API")

# Include routers
app.include_router(navigation_router)

@app.on_event("startup")
async def startup():
    # Initialize database tables
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    # Close database connections
    await close_db()

@app.get("/health")
async def health_check():
    from database import check_db_health
    db_healthy = await check_db_health()
    return {"status": "healthy" if db_healthy else "unhealthy", "database": db_healthy}
"""
