"""
Test script to verify database connection and basic queries.
Run this to check if everything is working correctly.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal, check_db_health, init_db
from database.models import SpeedCamera, RoadSpeedLimit, HazardDetection
from database.queries import get_nearby_speed_cameras, get_nearby_speed_limits


async def test_connection():
    """Test database connection."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1. Testing database health...")
    is_healthy = await check_db_health()
    if is_healthy:
        print("✓ Database connection is healthy")
    else:
        print("✗ Database connection failed!")
        return False
    
    # Test 2: Count records
    print("\n2. Counting records...")
    async with AsyncSessionLocal() as db:
        # Count cameras
        result = await db.execute(select(func.count(SpeedCamera.id)))
        camera_count = result.scalar()
        print(f"  Speed Cameras: {camera_count}")
        
        # Count speed limits
        result = await db.execute(select(func.count(RoadSpeedLimit.id)))
        speed_limit_count = result.scalar()
        print(f"  Speed Limits: {speed_limit_count}")
        
        # Count hazards
        result = await db.execute(select(func.count(HazardDetection.id)))
        hazard_count = result.scalar()
        print(f"  Hazards: {hazard_count}")
    
    # Test 3: Sample query (Chennai coordinates)
    print("\n3. Testing spatial queries...")
    chennai_lat = 13.0827
    chennai_lon = 80.2707
    
    async with AsyncSessionLocal() as db:
        print(f"  Querying cameras near Chennai ({chennai_lat}, {chennai_lon})...")
        cameras = await get_nearby_speed_cameras(
            db=db,
            latitude=chennai_lat,
            longitude=chennai_lon,
            radius_meters=5000.0,  # 5km radius
            limit=10
        )
        print(f"  Found {len(cameras)} cameras within 5km")
        
        if cameras:
            print(f"  Sample camera: {cameras[0].camera_type}, {cameras[0].speed_limit_kmh}km/h")
        
        print(f"  Querying speed limits near Chennai...")
        speed_limits = await get_nearby_speed_limits(
            db=db,
            latitude=chennai_lat,
            longitude=chennai_lon,
            radius_meters=2000.0,  # 2km radius
            limit=10
        )
        print(f"  Found {len(speed_limits)} speed limits within 2km")
        
        if speed_limits:
            print(f"  Sample speed limit: {speed_limits[0].road_name or 'Unknown'}, {speed_limits[0].speed_limit_kmh}km/h")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


async def main():
    """Main test function."""
    try:
        # Initialize database
        await init_db()
        
        # Run tests
        success = await test_connection()
        
        if success:
            print("\n✓ Database is ready to use!")
        else:
            print("\n✗ Database tests failed. Please check your configuration.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
