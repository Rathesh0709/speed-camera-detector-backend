import sys
from pathlib import Path

# Add database folder to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, Depends, Query, HTTPException, status, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import os
import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr
import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta

from database.database import get_db, init_db, close_db, check_db_health
from database.queries import (
    get_nearby_speed_cameras,
    get_nearby_speed_limits,
    get_nearby_hazards,
    get_nearby_school_zones,
    get_nearby_hospital_zones,
    create_speed_camera,
    get_all_school_zones,
    create_school_zone,
    get_all_hospital_zones,
    create_hospital_zone,
    get_nearby_hazardous_roads,
    create_hazardous_road_segment,
    create_hazard_report,
)
from database.models import (
    SpeedCamera,
    RoadSpeedLimit,
    User,
    HazardDetection,
    SchoolZone,
    HospitalZone,
    HazardousRoadSegment,
    HazardReport,
)

app = FastAPI(title="Navigation App Backend")

# CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
os.makedirs("static/hazards", exist_ok=True)
os.makedirs("static/profiles", exist_ok=True)

# Mount static files to serve hazard images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load models once
road_model = YOLO("models/best.pt")
general_model = YOLO("yolov8s.pt")

RELEVANT_CLASSES = [0, 1, 2, 3, 5, 7, 9, 11]

# Password hashing (bcrypt directly; no passlib to avoid version clashes)
security = HTTPBearer()

# Pydantic models for requests/responses
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    profile_photo_url: Optional[str] = None
    trips_count: int = 0
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    user: UserResponse

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None

class CreateCameraRequest(BaseModel):
    latitude: float
    longitude: float
    speed_limit_kmh: int
    camera_type: str = "fixed"
    direction_degrees: Optional[int] = None
    notes: Optional[str] = None

@app.post("/detect-frame")
async def detect_frame(file: UploadFile = File(...)):
    # Decode image
    image_bytes = await file.read()
    frame = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    detections = {
        "road_damage": [],
        "general_objects": []
    }

    # Get frame dimensions
    h, w = frame.shape[:2]

    # ---------- ROAD DAMAGE ----------
    road_results = road_model(frame, conf=0.15, verbose=False)
    for box in road_results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls = int(box.cls)
        conf = float(box.conf)
        label = f"{road_model.names[cls]} {conf:.2f}"

        detections["road_damage"].append({
            "class": road_model.names[cls],
            "confidence": conf,
            "bbox": [x1 / w, y1 / h, x2 / w, y2 / h]
        })

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(frame, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # ---------- GENERAL OBJECTS ----------
    general_results = general_model(frame, conf=0.25, verbose=False)
    for box in general_results[0].boxes:
        cls = int(box.cls)
        if cls in RELEVANT_CLASSES:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf)
            label = f"{general_model.names[cls]} {conf:.2f}"

            detections["general_objects"].append({
                "class": general_model.names[cls],
                "confidence": conf,
                "bbox": [x1 / w, y1 / h, x2 / w, y2 / h]
            })

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Encode image to Base64
    _, buffer = cv2.imencode(".jpg", frame)
    img_base64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "image": img_base64,
        "detections": detections
    }


# ============================================
# Database Lifecycle Events
# ============================================

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()
    print("✓ Database initialized")


@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown."""
    await close_db()
    print("✓ Database connections closed")


# ============================================
# Health Check Endpoints
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await check_db_health()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected"
    }

# ============================================
# Authentication Endpoints
# ============================================

# Bcrypt accepts at most 72 bytes. We use SHA-256 to get a fixed 64-byte input (no limit on user password length).
def _password_to_bcrypt_bytes(password: str) -> bytes:
    """Normalize password to a fixed 64-byte value for bcrypt (SHA-256 hex)."""
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raw = raw[:72]
    return hashlib.sha256(raw).hexdigest().encode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a stored bcrypt hash."""
    if not hashed_password or not hashed_password.startswith("$2"):
        return False
    try:
        return bcrypt.checkpw(
            _password_to_bcrypt_bytes(plain_password),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash a password (any length) with SHA-256 + bcrypt. Returns str for DB storage."""
    hashed = bcrypt.hashpw(
        _password_to_bcrypt_bytes(password),
        bcrypt.gensalt(),
    )
    return hashed.decode("utf-8")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from token."""
    from uuid import UUID
    token = credentials.credentials
    # Simple token validation - in production, use JWT
    try:
        user_id = UUID(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    try:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Check if username already exists
        result = await db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}",
        )

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get access token."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    # Generate simple token (in production, use JWT)
    token = str(user.id)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
        )
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        profile_photo_url=current_user.profile_photo_url,
        trips_count=current_user.trips_count or 0,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@app.put("/api/auth/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile (name)."""
    try:
        if profile_data.full_name is not None:
            current_user.full_name = profile_data.full_name
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            full_name=current_user.full_name,
            profile_photo_url=current_user.profile_photo_url,
            trips_count=current_user.trips_count or 0,
            created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


@app.post("/api/auth/profile/photo", response_model=UserResponse)
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and update profile photo."""
    try:
        os.makedirs("static/profiles", exist_ok=True)
        file_extension = os.path.splitext(photo.filename)[1] if photo.filename else ".jpg"
        file_name = f"{current_user.id}{file_extension}"
        file_path = os.path.join("static/profiles", file_name)
        
        with open(file_path, "wb") as buffer:
            content = await photo.read()
            buffer.write(content)
        
        current_user.profile_photo_url = f"/static/profiles/{file_name}"
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            full_name=current_user.full_name,
            profile_photo_url=current_user.profile_photo_url,
            trips_count=current_user.trips_count or 0,
            created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading photo: {str(e)}")


@app.post("/api/auth/increment-trips", response_model=UserResponse)
async def increment_trips(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Increment user's trip count."""
    try:
        current_user.trips_count = (current_user.trips_count or 0) + 1
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            full_name=current_user.full_name,
            profile_photo_url=current_user.profile_photo_url,
            trips_count=current_user.trips_count or 0,
            created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error incrementing trips: {str(e)}")


# ============================================
# Speed Camera Endpoints
# ============================================

@app.get("/api/cameras/nearby")
async def get_cameras_nearby(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_meters: float = Query(1000.0, gt=0, le=100000, description="Search radius in meters (max 100km)"),
    limit: int = Query(50, gt=0, le=500, description="Max number of cameras to return"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    verified_only: bool = Query(False, description="Only return verified cameras"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get speed cameras near a location.
    """
    try:
        cameras = await get_nearby_speed_cameras(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            min_confidence=min_confidence,
            verified_only=verified_only,
            limit=limit,
        )
        
        # Convert to response format
        # Extract coordinates: cast geography to geometry for ST_X/ST_Y (PostGIS requirement)
        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry

        camera_ids = [camera.id for camera in cameras]
        coords_dict = {}
        if camera_ids:
            coords_result = await db.execute(
                select(
                    SpeedCamera.id,
                    func.ST_Y(cast(SpeedCamera.location, Geometry)).label('lat'),
                    func.ST_X(cast(SpeedCamera.location, Geometry)).label('lon'),
                ).where(SpeedCamera.id.in_(camera_ids))
            )
            for row in coords_result:
                lat = float(row.lat) if row.lat is not None else None
                lon = float(row.lon) if row.lon is not None else None
                coords_dict[row.id] = (lat, lon)

        result = []
        for camera in cameras:
            lat, lon = coords_dict.get(camera.id, (None, None))
            # Omit cameras with invalid coords so app doesn't get null
            if lat is None or lon is None:
                continue
            result.append({
                "id": str(camera.id),
                "latitude": lat,
                "longitude": lon,
                "speed_limit_kmh": camera.speed_limit_kmh,
                "camera_type": camera.camera_type,
                "direction_degrees": camera.direction_degrees,
                "verified": camera.verified,
                "confidence_score": float(camera.confidence_score or 0),
                "notes": camera.notes,
                "reported_by": str(camera.reported_by) if camera.reported_by else None,
            })

        return {"cameras": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cameras: {str(e)}")


@app.get("/api/cameras")
async def get_all_cameras(
    limit: int = Query(1000, gt=0, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Get all speed cameras (unfiltered by location)."""
    try:
        from sqlalchemy import select
        result = await db.execute(select(SpeedCamera).limit(limit))
        cameras = result.scalars().all()
        
        from sqlalchemy import cast, func
        from geoalchemy2.types import Geometry

        camera_ids = [camera.id for camera in cameras]
        coords_dict = {}
        if camera_ids:
            coords_result = await db.execute(
                select(
                    SpeedCamera.id,
                    func.ST_Y(cast(SpeedCamera.location, Geometry)).label('lat'),
                    func.ST_X(cast(SpeedCamera.location, Geometry)).label('lon'),
                ).where(SpeedCamera.id.in_(camera_ids))
            )
            for row in coords_result:
                coords_dict[row.id] = (float(row.lat), float(row.lon))

        final_result = []
        for camera in cameras:
            lat, lon = coords_dict.get(camera.id, (None, None))
            if lat is None or lon is None:
                continue
            final_result.append({
                "id": str(camera.id),
                "latitude": lat,
                "longitude": lon,
                "speed_limit_kmh": camera.speed_limit_kmh,
                "camera_type": camera.camera_type,
                "direction_degrees": camera.direction_degrees,
                "verified": camera.verified,
                "confidence_score": float(camera.confidence_score or 0),
                "notes": camera.notes,
                "reported_by": str(camera.reported_by) if camera.reported_by else None,
            })

        return {"cameras": final_result, "count": len(final_result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching all cameras: {str(e)}")


@app.get("/api/cameras/count")
async def get_cameras_count(db: AsyncSession = Depends(get_db)):
    """Get total count of speed cameras."""
    from sqlalchemy import select, func
    result = await db.execute(select(func.count(SpeedCamera.id)))
    count = result.scalar()
    return {"total_cameras": count}


# ============================================
# Speed Limit Endpoints
# ============================================

@app.get("/api/speed-limits/nearby")
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
    try:
        speed_limits = await get_nearby_speed_limits(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            min_confidence=min_confidence,
            verified_only=verified_only,
        )
        
        # Extract coordinates from linestring geometry for map markers
        from sqlalchemy import func, select, cast
        from geoalchemy2.types import Geometry
        
        result = []
        for speed_limit in speed_limits:
            # Get centroid of the linestring as a representative point
            try:
                coords_result = await db.execute(
                    select(
                        func.ST_Y(func.ST_Centroid(speed_limit.road_segment)).label('lat'),
                        func.ST_X(func.ST_Centroid(speed_limit.road_segment)).label('lon'),
                    ).where(RoadSpeedLimit.id == speed_limit.id)
                )
                coords_row = coords_result.first()
                lat, lon = (float(coords_row.lat), float(coords_row.lon)) if coords_row else (None, None)
            except Exception as e:
                print(f"Error extracting coordinates for speed limit {speed_limit.id}: {e}")
                lat, lon = None, None
            
            result.append({
                "id": str(speed_limit.id),
                "speed_limit_kmh": speed_limit.speed_limit_kmh,
                "road_name": speed_limit.road_name,
                "road_type": speed_limit.road_type,
                "direction": speed_limit.direction,
                "verified": speed_limit.verified,
                "confidence_score": float(speed_limit.confidence_score),
                "notes": speed_limit.notes,
                "latitude": lat,
                "longitude": lon,
            })
        
        return {"speed_limits": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching speed limits: {str(e)}")


class CreateHazardRequest(BaseModel):
    latitude: float
    longitude: float
    hazard_type: str
    severity: str = "medium"
    confidence_score: float = 0.50
    description: Optional[str] = None

@app.post("/api/hazards", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_hazard(
    latitude: float = Form(...),
    longitude: float = Form(...),
    hazard_type: str = Form(...),
    severity: str = Form("medium"),
    confidence_score: float = Form(0.50),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new hazard detection report with optional image upload."""
    try:
        image_url = None
        if image:
            # Save uploaded image to static/hazards
            file_extension = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
            file_name = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join("static/hazards", file_name)
            
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            image_url = f"/static/hazards/{file_name}"

        from database.queries import create_hazard_detection
        hazard = await create_hazard_detection(
            db=db,
            latitude=latitude,
            longitude=longitude,
            hazard_type=hazard_type,
            severity=severity,
            confidence_score=confidence_score,
            detected_by=current_user.id,
            description=description,
            image_url=image_url,
        )
        await db.commit()
        
        return {
            "id": str(hazard.id),
            "hazard_type": hazard.hazard_type,
            "severity": hazard.severity,
            "confidence_score": float(hazard.confidence_score),
            "detected_at": hazard.detected_at.isoformat(),
            "image_url": image_url,
        }
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating hazard: {str(e)}")


@app.get("/api/hazards/roads/nearby")
async def get_hazardous_roads_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(1000.0, gt=0, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Get hazardous road segments near a location."""
    try:
        roads = await get_nearby_hazardous_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )
        
        # Format for response (need ST_AsGeoJSON or similar for lines)
        from sqlalchemy import func, select, cast
        from geoalchemy2.types import Geometry
        
        result = []
        for road in roads:
            # Get geometry as GeoJSON
            geo_result = await db.execute(
                select(func.ST_AsGeoJSON(cast(road.road_segment, Geometry)))
            )
            geojson = geo_result.scalar()
            
            result.append({
                "id": str(road.id),
                "hazard_type": road.hazard_type,
                "severity": road.severity,
                "road_name": road.road_name,
                "confidence_score": float(road.confidence_score),
                "geojson": geojson,
            })
        
        return {"roads": result, "count": len(result)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching hazardous roads: {str(e)}")


@app.post("/api/reports", status_code=status.HTTP_201_CREATED)
async def report_hazard(
    latitude: float = Form(...),
    longitude: float = Form(...),
    report_type: str = Form(...),
    reason: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User report for a camera zone or hazard with reason."""
    try:
        image_url = None
        if image:
            os.makedirs("static/reports", exist_ok=True)
            file_extension = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
            file_name = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join("static/reports", file_name)
            
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            image_url = f"/static/reports/{file_name}"

        report = await create_hazard_report(
            db=db,
            user_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            report_type=report_type,
            reason=reason,
            image_url=image_url,
        )
        await db.commit()
        
        return {"id": str(report.id), "message": "Report submitted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting report: {str(e)}")


@app.post("/api/hazards/detect-and-save")
async def detect_and_save_hazard(
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect road damage from photo and save as hazard if detected."""
    try:
        # 1. Save and detect
        image_bytes = await image.read()
        frame = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        results = road_model(frame, conf=0.25, verbose=False)
        detected_damages = []
        for box in results[0].boxes:
            cls = int(box.cls)
            conf = float(box.conf)
            detected_damages.append({
                "type": road_model.names[cls],
                "confidence": conf
            })
        
        if not detected_damages:
            return {"status": "no_damage_detected", "message": "Model did not detect any road damage."}
        
        # 2. Save image
        file_name = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join("static/hazards", file_name)
        cv2.imwrite(file_path, frame)
        image_url = f"/static/hazards/{file_name}"
        
        # 3. Save to DB
        primary_damage = sorted(detected_damages, key=lambda x: x["confidence"], reverse=True)[0]
        
        from database.queries import create_hazard_detection
        hazard = await create_hazard_detection(
            db=db,
            latitude=latitude,
            longitude=longitude,
            hazard_type=primary_damage["type"],
            severity="high" if primary_damage["confidence"] > 0.7 else "medium",
            confidence_score=primary_damage["confidence"],
            detected_by=current_user.id,
            description=f"Auto-detected {primary_damage['type']} via photo upload.",
            image_url=image_url,
        )
        await db.commit()
        
        return {
            "status": "damage_detected",
            "hazard_type": primary_damage["type"],
            "confidence": primary_damage["confidence"],
            "image_url": image_url
        }
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in detect-and-save: {str(e)}")


@app.get("/api/speed-limits/count")
async def get_speed_limits_count(db: AsyncSession = Depends(get_db)):
    """Get total count of speed limits."""
    from sqlalchemy import select, func
    result = await db.execute(select(func.count(RoadSpeedLimit.id)))
    count = result.scalar()
    return {"total_speed_limits": count}


# ============================================
# Combined Navigation Data Endpoint
# ============================================

@app.get("/api/navigation/nearby")
async def get_navigation_data_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(1000.0, gt=0, le=100000),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all navigation data (cameras, speed limits, hazards) near a location.
    Useful for Flutter app to get all data in one request.
    """
    try:
        cameras = await get_nearby_speed_cameras(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            min_confidence=0.0,
            verified_only=False,
        )
        
        speed_limits = await get_nearby_speed_limits(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            min_confidence=0.0,
            verified_only=False,
        )
        
        hazards = await get_nearby_hazards(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            min_confidence=0.0,
            active_only=True,
        )

        hazardous_roads = await get_nearby_hazardous_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )
        
        # Format cameras
        cameras_data = []
        for camera in cameras:
            cameras_data.append({
                "id": str(camera.id),
                "speed_limit_kmh": camera.speed_limit_kmh,
                "camera_type": camera.camera_type,
                "direction_degrees": camera.direction_degrees,
                "verified": camera.verified,
                "confidence_score": float(camera.confidence_score),
            })
        
        # Format speed limits
        speed_limits_data = []
        for speed_limit in speed_limits:
            speed_limits_data.append({
                "id": str(speed_limit.id),
                "speed_limit_kmh": speed_limit.speed_limit_kmh,
                "road_name": speed_limit.road_name,
                "road_type": speed_limit.road_type,
                "verified": speed_limit.verified,
                "confidence_score": float(speed_limit.confidence_score),
            })
        
        # Format hazards
        hazards_data = []
        
        # Extract hazard coordinates (PostGIS geography -> geometry)
        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry
        
        hazard_ids = [h.id for h in hazards]
        hazard_coords = {}
        if hazard_ids:
            h_coords_result = await db.execute(
                select(
                    HazardDetection.id,
                    func.ST_Y(cast(HazardDetection.location, Geometry)).label('lat'),
                    func.ST_X(cast(HazardDetection.location, Geometry)).label('lon'),
                ).where(HazardDetection.id.in_(hazard_ids))
            )
            for row in h_coords_result.all():
                hazard_coords[row.id] = (float(row.lat), float(row.lon))

        for hazard in hazards:
            lat, lon = hazard_coords.get(hazard.id, (None, None))
            hazards_data.append({
                "id": str(hazard.id),
                "hazard_type": hazard.hazard_type,
                "severity": hazard.severity,
                "confidence_score": float(hazard.confidence_score),
                "is_active": hazard.is_active,
                "detected_at": hazard.detected_at.isoformat() if hazard.detected_at else None,
                "image_url": hazard.image_url,
                "latitude": lat,
                "longitude": lon,
                "description": hazard.description,
            })
        
        # Format hazardous roads
        roads_data = []
        from sqlalchemy import func, select, cast
        from geoalchemy2.types import Geometry

        for road in hazardous_roads:
            # Get geometry as GeoJSON
            geo_result = await db.execute(
                select(func.ST_AsGeoJSON(cast(road.road_segment, Geometry)))
            )
            geojson = geo_result.scalar()
            
            roads_data.append({
                "id": str(road.id),
                "hazard_type": road.hazard_type,
                "severity": road.severity,
                "road_name": road.road_name,
                "confidence_score": float(road.confidence_score),
                "geojson": geojson,
            })
        
        return {
            "cameras": cameras_data,
            "speed_limits": speed_limits_data,
            "hazards": hazards_data,
            "hazardous_roads": roads_data,
            "counts": {
                "cameras": len(cameras_data),
                "speed_limits": len(speed_limits_data),
                "hazards": len(hazards_data),
                "hazardous_roads": len(roads_data),
            }
        }
    except Exception as e:
        import traceback
        print(f"Navigation nearby error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching navigation data: {str(e)}")


# ============================================
# School and Hospital Zone Endpoints
# ============================================

@app.get("/api/zones/schools")
async def get_all_schools(
    limit: int = Query(50000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get all school zones."""
    try:
        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry

        # Optimized query: Fetch model and coordinates in one go
        query = select(
            SchoolZone,
            func.ST_Y(cast(SchoolZone.location, Geometry)).label("lat"),
            func.ST_X(cast(SchoolZone.location, Geometry)).label("lon")
        ).order_by(SchoolZone.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        rows = result.all()
        
        final_result = []
        for school, lat, lon in rows:
            if lat is None or lon is None:
                continue
            final_result.append({
                "id": str(school.id),
                "name": school.name,
                "address": school.address,
                "latitude": float(lat),
                "longitude": float(lon),
                "type": "school",
            })
        
        return {"zones": final_result, "count": len(final_result)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching school zones: {str(e)}")


@app.post("/api/zones/schools", status_code=201)
async def create_school(
    zone: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new school zone."""
    try:
        new_zone = await create_school_zone(
            db=db,
            latitude=zone["latitude"],
            longitude=zone["longitude"],
            name=zone["name"],
            address=zone.get("address"),
        )
        return {"id": str(new_zone.id), "message": "School zone created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating school zone: {str(e)}")


@app.get("/api/zones/schools/nearby")
async def get_schools_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(300.0, gt=0, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Get school zones near a location (default 300m for alerts)."""
    try:
        schools = await get_nearby_school_zones(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )

        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry

        school_ids = [s.id for s in schools]
        coords_dict = {}
        if school_ids:
            coords_result = await db.execute(
                select(
                    SchoolZone.id,
                    func.ST_Y(cast(SchoolZone.location, Geometry)).label("lat"),
                    func.ST_X(cast(SchoolZone.location, Geometry)).label("lon"),
                ).where(SchoolZone.id.in_(school_ids))
            )
            for row in coords_result:
                coords_dict[row.id] = (float(row.lat), float(row.lon))

        result = []
        for school in schools:
            lat, lon = coords_dict.get(school.id, (None, None))
            if lat is None or lon is None:
                continue
            result.append({
                "id": str(school.id),
                "name": school.name,
                "address": school.address,
                "latitude": lat,
                "longitude": lon,
                "type": "school",
            })

        return {"zones": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching school zones: {str(e)}")


@app.get("/api/zones/hospitals")
async def get_all_hospitals(
    limit: int = Query(50000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get all hospital zones."""
    try:
        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry

        # Optimized query: Fetch model and coordinates in one go
        query = select(
            HospitalZone,
            func.ST_Y(cast(HospitalZone.location, Geometry)).label("lat"),
            func.ST_X(cast(HospitalZone.location, Geometry)).label("lon")
        ).order_by(HospitalZone.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        rows = result.all()
        
        final_result = []
        for hospital, lat, lon in rows:
            if lat is None or lon is None:
                continue
            final_result.append({
                "id": str(hospital.id),
                "name": hospital.name,
                "address": hospital.address,
                "latitude": float(lat),
                "longitude": float(lon),
                "type": "hospital",
            })
        
        return {"zones": final_result, "count": len(final_result)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching hospital zones: {str(e)}")


@app.post("/api/zones/hospitals", status_code=201)
async def create_hospital(
    zone: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new hospital zone."""
    try:
        new_zone = await create_hospital_zone(
            db=db,
            latitude=zone["latitude"],
            longitude=zone["longitude"],
            name=zone["name"],
            address=zone.get("address"),
        )
        return {"id": str(new_zone.id), "message": "Hospital zone created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating hospital zone: {str(e)}")


@app.get("/api/zones/hospitals/nearby")
async def get_hospitals_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(300.0, gt=0, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Get hospital zones near a location (default 300m for alerts)."""
    try:
        hospitals = await get_nearby_hospital_zones(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )

        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry

        hospital_ids = [h.id for h in hospitals]
        coords_dict = {}
        if hospital_ids:
            coords_result = await db.execute(
                select(
                    HospitalZone.id,
                    func.ST_Y(cast(HospitalZone.location, Geometry)).label("lat"),
                    func.ST_X(cast(HospitalZone.location, Geometry)).label("lon"),
                ).where(HospitalZone.id.in_(hospital_ids))
            )
            for row in coords_result:
                coords_dict[row.id] = (float(row.lat), float(row.lon))

        result = []
        for hospital in hospitals:
            lat, lon = coords_dict.get(hospital.id, (None, None))
            if lat is None or lon is None:
                continue
            result.append({
                "id": str(hospital.id),
                "name": hospital.name,
                "address": hospital.address,
                "latitude": lat,
                "longitude": lon,
                "type": "hospital",
            })

        return {"zones": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching hospital zones: {str(e)}")




# ============================================
# Speed Camera Creation
# ============================================

@app.post("/api/cameras", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_camera(
    request: CreateCameraRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new speed camera report."""
    try:
        camera = await create_speed_camera(
            db=db,
            latitude=request.latitude,
            longitude=request.longitude,
            speed_limit_kmh=request.speed_limit_kmh,
            camera_type=request.camera_type,
            direction_degrees=request.direction_degrees,
            confidence_score=0.50,  # User-reported cameras start with lower confidence
            reported_by=current_user.id,
            notes=request.notes,
        )
        await db.commit()
        
        # Get coordinates for response (cast geography to geometry for ST_X/ST_Y)
        from sqlalchemy import cast, func, select
        from geoalchemy2.types import Geometry

        coords_result = await db.execute(
            select(
                func.ST_Y(cast(SpeedCamera.location, Geometry)).label('lat'),
                func.ST_X(cast(SpeedCamera.location, Geometry)).label('lon'),
            ).where(SpeedCamera.id == camera.id)
        )
        coords_row = coords_result.first()
        lat, lon = (float(coords_row.lat), float(coords_row.lon)) if coords_row else (request.latitude, request.longitude)
        
        return {
            "id": str(camera.id),
            "latitude": lat,
            "longitude": lon,
            "speed_limit_kmh": camera.speed_limit_kmh,
            "camera_type": camera.camera_type,
            "direction_degrees": camera.direction_degrees,
            "verified": camera.verified,
            "confidence_score": float(camera.confidence_score),
            "notes": camera.notes,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating camera: {str(e)}")


@app.delete("/api/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a speed camera. Only the user who reported it can delete."""
    from uuid import UUID
    try:
        cam_uuid = UUID(camera_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid camera ID")
    result = await db.execute(select(SpeedCamera).where(SpeedCamera.id == cam_uuid))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if camera.reported_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete cameras you added")
    await db.delete(camera)
    await db.commit()
