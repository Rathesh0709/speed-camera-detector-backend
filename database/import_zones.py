import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List
from urllib.parse import urlparse, urlunparse

# Add parent directory to path to import database modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Default DATABASE_URL
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:1634@localhost:5432/navigation_app"

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import AsyncSessionLocal, init_db
from database.models import SchoolZone, HospitalZone

async def import_zones(db: AsyncSession, json_file_path: str, zone_type: str) -> int:
    print(f"Reading {zone_type} zones from {json_file_path}...")
    
    # Pre-fetch existing OSM IDs to avoid duplicates
    existing_ids = set()
    try:
        if zone_type == 'school':
            result = await db.execute(select(SchoolZone.osm_id))
        else:
            result = await db.execute(select(HospitalZone.osm_id))
        
        for row in result.all():
            if row[0]:
                existing_ids.add(str(row[0]))
        print(f"  Found {len(existing_ids)} existing {zone_type} zones in DB. Skipping duplicates.")
    except Exception as e:
        print(f"  Warning: Could not fetch existing IDs: {e}")

    # Track seen IDs to handle duplicates within the JSON itself
    seen_ids = set(existing_ids)

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    elements = data.get('elements', [])
    print(f"Found {len(elements)} elements in JSON file")
    
    imported_count = 0
    skipped_count = 0
    duplicate_count = 0
    
    for element in elements:
        try:
            # We focus on nodes for individual points
            if element.get('type') != 'node':
                skipped_count += 1
                continue
                
            osm_id = str(element.get('id'))
            
            # Skip if already exists or seen in this run
            if osm_id in seen_ids:
                duplicate_count += 1
                continue
            
            # Mark as seen
            seen_ids.add(osm_id)
                
            lat = element.get('lat')
            lon = element.get('lon')
            tags = element.get('tags', {})
            name = tags.get('name') or tags.get('name:en') or f"Unnamed {zone_type}"
            
            # Extract address
            street = tags.get('addr:street')
            city = tags.get('addr:city')
            full_addr = tags.get('addr:full')
            address = full_addr or f"{street or ''}, {city or ''}".strip(", ")
            if not address:
                address = "Address not available"
            
            if lat is None or lon is None:
                skipped_count += 1
                continue
                
            # Create point geometry
            point_sql = text(f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)")
            
            if zone_type == 'school':
                zone = SchoolZone(
                    location=point_sql,
                    name=name,
                    address=address,
                    osm_id=osm_id
                )
            else:
                zone = HospitalZone(
                    location=point_sql,
                    name=name,
                    address=address,
                    osm_id=osm_id
                )
            
            db.add(zone)
            imported_count += 1
            
            # Commit in batches
            if imported_count % 500 == 0:
                await db.commit()
                print(f"  Imported {imported_count} {zone_type} zones...")
                
        except Exception as e:
            print(f"  Error importing {zone_type} node {element.get('id')}: {e}")
            skipped_count += 1
            continue
            
    await db.commit()
    print(f"  Imported {imported_count} {zone_type} zones (skipped {skipped_count}, duplicates {duplicate_count})")
    return imported_count

async def main():
    print("=" * 60)
    print("Navigation App - Zone Data Import Script")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    school_file = script_dir / "school_zones.json"
    hospital_file = script_dir / "hospital_zones.json"
    
    print("\n1. Initializing database schema...")
    await init_db()
    print("[OK] Database initialized")
    
    async with AsyncSessionLocal() as db:
        print("\n2. Importing school zones...")
        if school_file.exists():
            await import_zones(db, str(school_file), 'school')
        else:
            print(f"WARNING: School zones file not found: {school_file}")
            
        print("\n3. Importing hospital zones...")
        if hospital_file.exists():
            await import_zones(db, str(hospital_file), 'hospital')
        else:
            print(f"WARNING: Hospital zones file not found: {hospital_file}")

    print("\n" + "=" * 60)
    print("Import Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
