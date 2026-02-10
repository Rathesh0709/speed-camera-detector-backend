"""
Helper functions for working with PostGIS geometry in SQLAlchemy.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def extract_point_coordinates(
    db: AsyncSession, geometry_column, record_id
) -> tuple[float, float]:
    """
    Extract latitude and longitude from a PostGIS POINT geometry.
    
    Args:
        db: Database session
        geometry_column: The geometry column (e.g., SpeedCamera.location)
        record_id: The record ID
    
    Returns:
        Tuple of (latitude, longitude)
    """
    # Use ST_Y and ST_X to extract coordinates
    # Note: ST_Y returns latitude, ST_X returns longitude
    result = await db.execute(
        select(
            func.ST_Y(geometry_column).label('lat'),
            func.ST_X(geometry_column).label('lon')
        ).where(geometry_column.table.c.id == record_id)
    )
    row = result.first()
    if row:
        return (float(row.lat), float(row.lon))
    return (None, None)


def format_camera_response(camera) -> dict:
    """
    Format a SpeedCamera model instance to a response dict.
    Note: This is a synchronous helper. For async, use extract_point_coordinates.
    """
    return {
        "id": str(camera.id),
        "speed_limit_kmh": camera.speed_limit_kmh,
        "camera_type": camera.camera_type,
        "direction_degrees": camera.direction_degrees,
        "verified": camera.verified,
        "confidence_score": float(camera.confidence_score),
        "notes": camera.notes,
    }
