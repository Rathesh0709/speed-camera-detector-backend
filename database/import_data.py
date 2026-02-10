"""
Script to import speed camera and speed limit data from JSON files into PostgreSQL.
Run this after creating the database schema.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse, urlunparse

# Add parent directory to path to import database modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix: Sanitize DATABASE_URL before importing modules that use it
if not os.getenv("DATABASE_URL"):
    # Default to user provided credentials
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:1634@localhost:5432/navigation_app"
else:
    # Strip whitespace from DATABASE_URL and ensure /navigation_app path
    url = os.getenv("DATABASE_URL").strip()
    try:
        parsed = urlparse(url)
        if not parsed.path or parsed.path == '/':
            parsed = parsed._replace(path="/navigation_app")
            url = urlunparse(parsed)
    except:
        pass
    os.environ["DATABASE_URL"] = url

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal, init_db
from database.models import RoadSpeedLimit, SpeedCamera


async def import_speed_cameras(db: AsyncSession, json_file_path: str) -> int:
    """
    Import speed cameras from JSON file.
    
    Args:
        db: Database session
        json_file_path: Path to the JSON file
    
    Returns:
        Number of cameras imported
    """
    print(f"Reading speed cameras from {json_file_path}...")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cameras_data = data.get('cameras', [])
    print(f"Found {len(cameras_data)} cameras in JSON file")
    
    imported_count = 0
    skipped_count = 0
    
    for cam_data in cameras_data:
        try:
            # Extract data
            latitude = float(cam_data.get('latitude', 0))
            longitude = float(cam_data.get('longitude', 0))
            
            # Skip if coordinates are invalid
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                skipped_count += 1
                continue
            
            # Parse speed limit (can be string like "80" or "/")
            speed_limit_str = str(cam_data.get('speed_limit', '0'))
            try:
                speed_limit_kmh = int(speed_limit_str) if speed_limit_str != '/' else 60  # Default to 60 if not specified
            except (ValueError, TypeError):
                speed_limit_kmh = 60
            
            # Map camera type
            camera_type_map = {
                'G': 'fixed',
                'M': 'mobile',
                'A': 'average_speed'
            }
            camera_type_char = cam_data.get('camera_type', 'G')
            camera_type = camera_type_map.get(camera_type_char, 'fixed')
            
            # Parse direction (can be string like "90" or None)
            direction_str = cam_data.get('direction')
            direction_degrees = None
            if direction_str:
                try:
                    direction_degrees = int(direction_str)
                    if not (0 <= direction_degrees <= 360):
                        direction_degrees = None
                except (ValueError, TypeError):
                    direction_degrees = None
            
            # Create point geometry using PostGIS function
            point_sql = text(f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)")
            
            # Check if camera already exists (by location, within 10 meters)
            # SpeedCamera.location is Geography. We must cast our point to Geography too
            # to ensure ST_DWithin uses meters, not degrees.
            existing = await db.execute(
                select(SpeedCamera).where(
                    func.ST_DWithin(
                        SpeedCamera.location,
                        text(f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)::geography"),
                        10.0  # 10 meters tolerance
                    )
                ).limit(1)  # Ensure we only fetch one
            )
            if existing.scalar():
                skipped_count += 1
                continue
            
            # Create camera record
            camera = SpeedCamera(
                location=point_sql,
                speed_limit_kmh=speed_limit_kmh,
                camera_type=camera_type,
                direction_degrees=direction_degrees,
                confidence_score=0.80,  # Default confidence for imported data
                verified=True,  # Mark imported data as verified
                verification_count=1,
                notes=f"Imported from {cam_data.get('street', 'Unknown')}, {cam_data.get('city', 'Unknown')}"
            )
            
            db.add(camera)
            imported_count += 1
            
            # Commit in batches of 100
            if imported_count % 100 == 0:
                await db.commit()
                print(f"  Imported {imported_count} cameras...")
        
        except Exception as e:
            print(f"  Error importing camera {cam_data.get('id', 'unknown')}: {e}")
            skipped_count += 1
            continue
    
    # Final commit
    await db.commit()
    print(f"  Imported {imported_count} speed cameras (skipped {skipped_count})")
    return imported_count


async def import_speed_limits(db: AsyncSession, json_file_path: str) -> int:
    """
    Import road speed limits from JSON file (OSM format).
    
    Args:
        db: Database session
        json_file_path: Path to the JSON file
    
    Returns:
        Number of speed limits imported
    """
    print(f"Reading speed limits from {json_file_path}...")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    elements = data.get('elements', [])
    print(f"Found {len(elements)} elements in JSON file")
    
    imported_count = 0
    skipped_count = 0
    
    for element in elements:
        try:
            # Only process ways (not nodes)
            if element.get('type') != 'way':
                continue
            
            # Get geometry
            geometry = element.get('geometry', [])
            if len(geometry) < 2:  # Need at least 2 points for a line
                skipped_count += 1
                continue
            
            # Get tags
            tags = element.get('tags', {})
            maxspeed_str = tags.get('maxspeed')
            
            # Skip if no speed limit specified
            if not maxspeed_str:
                skipped_count += 1
                continue
            
            # Parse speed limit (can be "40", "40 km/h", etc.)
            try:
                # Extract number from string
                speed_limit_kmh = int(''.join(filter(str.isdigit, str(maxspeed_str))))
                if speed_limit_kmh <= 0 or speed_limit_kmh > 200:
                    skipped_count += 1
                    continue
            except (ValueError, TypeError):
                skipped_count += 1
                continue
            
            # Extract coordinates (lat, lon) and convert to (lon, lat) for PostGIS
            coordinates = [(float(pt['lat']), float(pt['lon'])) for pt in geometry]
            
            # Build linestring SQL
            points_array = [f"ST_MakePoint({lon}, {lat})" for lat, lon in coordinates]
            linestring_sql = text(f"ST_SetSRID(ST_MakeLine(ARRAY[{', '.join(points_array)}]), 4326)")
            
            # Get road name and type
            road_name = tags.get('name') or tags.get('ref') or None
            road_type = tags.get('highway', 'unknown')
            
            # Determine direction
            direction = 'both'
            if tags.get('oneway') == 'yes':
                direction = 'forward'
            
            # Create speed limit record
            speed_limit = RoadSpeedLimit(
                road_segment=linestring_sql,
                speed_limit_kmh=speed_limit_kmh,
                road_name=road_name,
                road_type=road_type,
                direction=direction,
                confidence_score=0.85,  # Default confidence for OSM data
                verified=True,  # Mark OSM data as verified
                verification_count=1,
                notes=f"Imported from OpenStreetMap (way {element.get('id', 'unknown')})"
            )
            
            db.add(speed_limit)
            imported_count += 1
            
            # Commit in batches of 50 (speed limits are larger)
            if imported_count % 50 == 0:
                await db.commit()
                print(f"  Imported {imported_count} speed limits...")
        
        except Exception as e:
            print(f"  Error importing speed limit {element.get('id', 'unknown')}: {e}")
            skipped_count += 1
            continue
    
    # Final commit
    await db.commit()
    print(f"  Imported {imported_count} speed limits (skipped {skipped_count})")
    return imported_count


async def main():
    print("=" * 60)
    print("Navigation App - Data Import Script")
    print("=" * 60)

    script_dir = Path(__file__).parent

    camera_files = [
        "tn_complete_cameras_detailed.json",
        "Bengaluru_complete_cameras_detailed.json",
        "delhi_complete_cameras_detailed.json",
        "Hyderabad_complete_cameras_detailed.json",
        "Kolkata_complete_cameras_detailed.json",
        "MUMBAI_complete_cameras_detailed.json",
        "Dehradun_complete_cameras_detailed.json",
        "coimbatore_complete_cameras_detailed.json",
        "puducherry_complete_cameras_detailed.json",
        "nh44_madurai_to_tirunelveli_complete_cameras_detailed.json",
        "KERALA_1_complete_cameras_detailed.json",
        "KERALA_2_complete_cameras_detailed.json",
        "KERALA_3_complete_cameras_detailed.json",
        "KERALA_4_complete_cameras_detailed.json",
        "KERALA_5_complete_cameras_detailed.json",
        "KERALA_6_complete_cameras_detailed.json",
        "KERALA_7_complete_cameras_detailed.json",
        "Chandigarh_complete_cameras_detailed.json",
    ]

    camera_files = [script_dir / f for f in camera_files]

    speed_limits_file = script_dir / "chennai_speed_limit.json"

    missing_files = [f for f in camera_files if not f.exists()]
    if missing_files:
        print("\nERROR: Missing camera files:")
        for f in missing_files:
            print(f"  - {f}")
        return

    if not speed_limits_file.exists():
        print(f"\nERROR: Speed limits file not found: {speed_limits_file}")
        return

    print("\n1. Initializing database...")
    await init_db()
    print("[OK] Database initialized")

    total_cameras = 0

    async with AsyncSessionLocal() as db:
        print("\n2. Importing speed cameras...")
        for cam_file in camera_files:
            print(f"\nImporting {cam_file.name}")
            count = await import_speed_cameras(db, str(cam_file))
            total_cameras += count

        print("\n3. Importing speed limits...")
        speed_limits_count = await import_speed_limits(db, str(speed_limits_file))

    print("\n" + "=" * 60)
    print("Import Complete!")
    print(f"  Speed Cameras (total): {total_cameras}")
    print(f"  Speed Limits: {speed_limits_count}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 