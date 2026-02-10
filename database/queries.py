"""
Example query functions for fetching nearby cameras and speed limits.
Uses PostGIS spatial queries with async SQLAlchemy.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from geoalchemy2 import functions as geo_func
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import HazardDetection, HazardousRoadSegment, HazardReport, HospitalZone, RoadSpeedLimit, SchoolZone, SpeedCamera


async def get_nearby_school_zones(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_meters: float = 300.0,
    limit: int = 20,
) -> List[SchoolZone]:
    """
    Get school zones within a specified radius of a point.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    query = select(SchoolZone).where(
        func.ST_DWithin(SchoolZone.location, point, radius_meters)
    )
    distance_col = func.ST_Distance(SchoolZone.location, point).label("distance")
    query = query.add_columns(distance_col).order_by(distance_col).limit(limit)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_all_school_zones(
    db: AsyncSession, limit: int = 100, offset: int = 0
) -> List[SchoolZone]:
    query = select(SchoolZone).order_by(SchoolZone.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def create_school_zone(
    db: AsyncSession, latitude: float, longitude: float, name: str, address: str = None
) -> SchoolZone:
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    zone = SchoolZone(location=point, name=name, address=address)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


async def get_nearby_hospital_zones(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_meters: float = 300.0,
    limit: int = 20,
) -> List[HospitalZone]:
    """
    Get hospital zones within a specified radius of a point.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    query = select(HospitalZone).where(
        func.ST_DWithin(HospitalZone.location, point, radius_meters)
    )
    distance_col = func.ST_Distance(HospitalZone.location, point).label("distance")
    query = query.add_columns(distance_col).order_by(distance_col).limit(limit)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_all_hospital_zones(
    db: AsyncSession, limit: int = 100, offset: int = 0
) -> List[HospitalZone]:
    query = select(HospitalZone).order_by(HospitalZone.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def create_hospital_zone(
    db: AsyncSession, latitude: float, longitude: float, name: str, address: str = None
) -> HospitalZone:
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    zone = HospitalZone(location=point, name=name, address=address)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


async def get_nearby_speed_cameras(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_meters: float = 1000.0,
    min_confidence: float = 0.0,
    verified_only: bool = False,
    limit: int = 50,
) -> List[SpeedCamera]:
    """
    Get speed cameras within a specified radius of a point.
    
    Args:
        db: Database session
        latitude: Latitude of the center point
        longitude: Longitude of the center point
        radius_meters: Search radius in meters (default: 1000m = 1km)
        min_confidence: Minimum confidence score (0.0 to 1.0)
        verified_only: Only return verified cameras
        limit: Maximum number of results
    
    Returns:
        List of SpeedCamera objects sorted by distance
    """
    # Create point from lat/lon
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    # Build query
    query = select(SpeedCamera).where(
        func.ST_DWithin(
            SpeedCamera.location,
            point,
            radius_meters
        )
    )
    
    # Apply filters
    if min_confidence > 0:
        query = query.where(SpeedCamera.confidence_score >= min_confidence)
    
    if verified_only:
        query = query.where(SpeedCamera.verified == True)
    
    # Add distance calculation and order by distance (use column ref for SQLAlchemy 2)
    distance_col = func.ST_Distance(SpeedCamera.location, point).label('distance')
    query = query.add_columns(distance_col).order_by(distance_col).limit(limit)
    
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_nearby_speed_limits(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_meters: float = 500.0,
    min_confidence: float = 0.0,
    verified_only: bool = False,
    limit: int = 50,
) -> List[RoadSpeedLimit]:
    """
    Get road speed limits within a specified radius of a point.
    Uses ST_DWithin to find road segments that intersect or are near the point.
    
    Args:
        db: Database session
        latitude: Latitude of the center point
        longitude: Longitude of the center point
        radius_meters: Search radius in meters (default: 500m)
        min_confidence: Minimum confidence score (0.0 to 1.0)
        verified_only: Only return verified speed limits
        limit: Maximum number of results
    
    Returns:
        List of RoadSpeedLimit objects
    """
    # Create point from lat/lon
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    # Build query
    query = select(RoadSpeedLimit).where(
        func.ST_DWithin(
            RoadSpeedLimit.road_segment,
            point,
            radius_meters
        )
    )
    
    # Apply filters
    if min_confidence > 0:
        query = query.where(RoadSpeedLimit.confidence_score >= min_confidence)
    
    if verified_only:
        query = query.where(RoadSpeedLimit.verified == True)
    
    # Add distance calculation and order by distance (use column ref for SQLAlchemy 2)
    distance_col = func.ST_Distance(RoadSpeedLimit.road_segment, point).label('distance')
    query = query.add_columns(distance_col).order_by(distance_col).limit(limit)

    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_nearby_hazards(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_meters: float = 1000.0,
    min_confidence: float = 0.0,
    active_only: bool = True,
    limit: int = 50,
) -> List[HazardDetection]:
    """
    Get active hazard detections within a specified radius of a point.
    
    Args:
        db: Database session
        latitude: Latitude of the center point
        longitude: Longitude of the center point
        radius_meters: Search radius in meters (default: 1000m)
        min_confidence: Minimum confidence score (0.0 to 1.0)
        active_only: Only return active hazards (not expired)
        limit: Maximum number of results
    
    Returns:
        List of HazardDetection objects sorted by distance
    """
    # Create point from lat/lon
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    # Build query
    query = select(HazardDetection).where(
        func.ST_DWithin(
            HazardDetection.location,
            point,
            radius_meters
        )
    )
    
    # Apply filters
    if min_confidence > 0:
        query = query.where(HazardDetection.confidence_score >= min_confidence)
    
    if active_only:
        query = query.where(
            and_(
                HazardDetection.is_active == True,
                or_(
                    HazardDetection.expires_at.is_(None),
                    HazardDetection.expires_at > func.now()
                )
            )
        )
    
    # Add distance calculation and order by distance (use column ref for SQLAlchemy 2)
    distance_col = func.ST_Distance(HazardDetection.location, point).label('distance')
    query = query.add_columns(distance_col).order_by(distance_col).limit(limit)

    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_speed_cameras_along_route(
    db: AsyncSession,
    route_coordinates: List[tuple],  # List of (lat, lon) tuples
    buffer_meters: float = 100.0,
    min_confidence: float = 0.0,
    verified_only: bool = False,
) -> List[SpeedCamera]:
    """
    Get speed cameras along a route (linestring).
    
    Args:
        db: Database session
        route_coordinates: List of (latitude, longitude) tuples forming the route
        buffer_meters: Buffer distance from route line (default: 100m)
        min_confidence: Minimum confidence score
        verified_only: Only return verified cameras
    
    Returns:
        List of SpeedCamera objects
    """
    # Build linestring from coordinates
    # Create points array: PostGIS expects (lon, lat) order
    points_array = [f"ST_MakePoint({lon}, {lat})" for lat, lon in route_coordinates]
    linestring = text(f"ST_SetSRID(ST_MakeLine(ARRAY[{', '.join(points_array)}]), 4326)")
    
    # Build query
    query = select(SpeedCamera).where(
        func.ST_DWithin(
            SpeedCamera.location,
            linestring,
            buffer_meters
        )
    )
    
    # Apply filters
    if min_confidence > 0:
        query = query.where(SpeedCamera.confidence_score >= min_confidence)
    
    if verified_only:
        query = query.where(SpeedCamera.verified == True)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_speed_limits_along_route(
    db: AsyncSession,
    route_coordinates: List[tuple],  # List of (lat, lon) tuples
    buffer_meters: float = 50.0,
    min_confidence: float = 0.0,
    verified_only: bool = False,
) -> List[RoadSpeedLimit]:
    """
    Get road speed limits that intersect or are near a route.
    
    Args:
        db: Database session
        route_coordinates: List of (latitude, longitude) tuples forming the route
        buffer_meters: Buffer distance from route line (default: 50m)
        min_confidence: Minimum confidence score
        verified_only: Only return verified speed limits
    
    Returns:
        List of RoadSpeedLimit objects
    """
    # Build linestring from coordinates
    # Create points array: PostGIS expects (lon, lat) order
    points_array = [f"ST_MakePoint({lon}, {lat})" for lat, lon in route_coordinates]
    linestring = text(f"ST_SetSRID(ST_MakeLine(ARRAY[{', '.join(points_array)}]), 4326)")
    
    # Build query
    query = select(RoadSpeedLimit).where(
        func.ST_DWithin(
            RoadSpeedLimit.road_segment,
            linestring,
            buffer_meters
        )
    )
    
    # Apply filters
    if min_confidence > 0:
        query = query.where(RoadSpeedLimit.confidence_score >= min_confidence)
    
    if verified_only:
        query = query.where(RoadSpeedLimit.verified == True)
    
    result = await db.execute(query)
    return result.scalars().all()


async def create_speed_camera(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    speed_limit_kmh: int,
    camera_type: str,
    direction_degrees: Optional[int] = None,
    confidence_score: float = 0.50,
    reported_by: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> SpeedCamera:
    """
    Create a new speed camera record.
    
    Args:
        db: Database session
        latitude: Latitude of camera location
        longitude: Longitude of camera location
        speed_limit_kmh: Speed limit in km/h
        camera_type: Type of camera ('fixed', 'mobile', 'average_speed')
        direction_degrees: Direction in degrees (0-360), None if omnidirectional
        confidence_score: Confidence score (0.0 to 1.0)
        reported_by: UUID of user who reported it
        notes: Optional notes
    
    Returns:
        Created SpeedCamera object
    """
    # Create point geometry
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    camera = SpeedCamera(
        location=point,
        speed_limit_kmh=speed_limit_kmh,
        camera_type=camera_type,
        direction_degrees=direction_degrees,
        confidence_score=confidence_score,
        reported_by=reported_by,
        notes=notes,
    )
    
    db.add(camera)
    await db.flush()
    await db.refresh(camera)
    return camera


async def create_road_speed_limit(
    db: AsyncSession,
    coordinates: List[tuple],  # List of (lat, lon) tuples
    speed_limit_kmh: int,
    road_name: Optional[str] = None,
    road_type: Optional[str] = None,
    direction: Optional[str] = None,
    confidence_score: float = 0.50,
    reported_by: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> RoadSpeedLimit:
    """
    Create a new road speed limit record.
    
    Args:
        db: Database session
        coordinates: List of (latitude, longitude) tuples forming the road segment
        speed_limit_kmh: Speed limit in km/h
        road_name: Name of the road
        road_type: Type of road ('highway', 'urban', 'rural', 'residential')
        direction: Direction ('forward', 'backward', 'both')
        confidence_score: Confidence score (0.0 to 1.0)
        reported_by: UUID of user who reported it
        notes: Optional notes
    
    Returns:
        Created RoadSpeedLimit object
    """
    # Build linestring from coordinates
    # Create points array: PostGIS expects (lon, lat) order
    points_array = [f"ST_MakePoint({lon}, {lat})" for lat, lon in coordinates]
    linestring = text(f"ST_SetSRID(ST_MakeLine(ARRAY[{', '.join(points_array)}]), 4326)")
    
    speed_limit = RoadSpeedLimit(
        road_segment=linestring,
        speed_limit_kmh=speed_limit_kmh,
        road_name=road_name,
        road_type=road_type,
        direction=direction,
        confidence_score=confidence_score,
        reported_by=reported_by,
        notes=notes,
    )
    
    db.add(speed_limit)
    await db.flush()
    await db.refresh(speed_limit)
    return speed_limit


async def create_hazard_detection(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    hazard_type: str,
    severity: str = "medium",
    confidence_score: float = 0.50,
    detected_by: Optional[UUID] = None,
    description: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    image_url: Optional[str] = None,
) -> HazardDetection:
    """
    Create a new hazard detection record.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    hazard = HazardDetection(
        location=point,
        hazard_type=hazard_type,
        severity=severity,
        confidence_score=confidence_score,
        detected_by=detected_by,
        description=description,
        expires_at=expires_at,
        image_url=image_url,
    )
    
    db.add(hazard)
    await db.flush()
    await db.refresh(hazard)
    return hazard
async def get_nearby_hazardous_roads(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_meters: float = 1000.0,
    min_confidence: float = 0.0,
    limit: int = 50,
) -> List[HazardousRoadSegment]:
    """
    Get hazardous road segments within a specified radius of a point.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    query = select(HazardousRoadSegment).where(
        func.ST_DWithin(
            HazardousRoadSegment.road_segment,
            point,
            radius_meters
        )
    )
    
    if min_confidence > 0:
        query = query.where(HazardousRoadSegment.confidence_score >= min_confidence)
    
    distance_col = func.ST_Distance(HazardousRoadSegment.road_segment, point).label('distance')
    query = query.add_columns(distance_col).order_by(distance_col).limit(limit)

    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def create_hazardous_road_segment(
    db: AsyncSession,
    coordinates: List[tuple],
    hazard_type: str,
    severity: str = "medium",
    road_name: Optional[str] = None,
    osm_id: Optional[str] = None,
    confidence_score: float = 0.50,
    reported_by: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> HazardousRoadSegment:
    """
    Create a new hazardous road segment.
    """
    points_array = [f"ST_MakePoint({lon}, {lat})" for lat, lon in coordinates]
    linestring = text(f"ST_SetSRID(ST_MakeLine(ARRAY[{', '.join(points_array)}]), 4326)")
    
    segment = HazardousRoadSegment(
        road_segment=linestring,
        hazard_type=hazard_type,
        severity=severity,
        road_name=road_name,
        osm_id=osm_id,
        confidence_score=confidence_score,
        reported_by=reported_by,
        notes=notes,
    )
    
    db.add(segment)
    await db.flush()
    await db.refresh(segment)
    return segment


async def create_hazard_report(
    db: AsyncSession,
    user_id: UUID,
    latitude: float,
    longitude: float,
    report_type: str,
    reason: str,
    image_url: Optional[str] = None,
) -> HazardReport:
    """
    Create a new hazard or camera zone report.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    
    report = HazardReport(
        user_id=user_id,
        location=point,
        report_type=report_type,
        reason=reason,
        image_url=image_url,
    )
    
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report
