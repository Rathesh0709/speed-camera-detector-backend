
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, text
from database.database import AsyncSessionLocal
from database.models import SchoolZone, HospitalZone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def check():
    from geoalchemy2 import functions as func
    from geoalchemy2.types import Geometry
    from sqlalchemy import cast
    async with AsyncSessionLocal() as db:
        print("Checking School Zones...")
        
        # Get a random school with coordinates
        result = await db.execute(
            select(
                SchoolZone.name, 
                func.ST_Y(cast(SchoolZone.location, Geometry)).label('lat'), 
                func.ST_X(cast(SchoolZone.location, Geometry)).label('lon')
            ).limit(1)
        )
        school = result.first()
        if school:
            print(f"Sample School: {school.name} at {school.lat}, {school.lon}")
        
        # Get a random hospital
        result = await db.execute(
            select(
                HospitalZone.name, 
                func.ST_Y(cast(HospitalZone.location, Geometry)).label('lat'), 
                func.ST_X(cast(HospitalZone.location, Geometry)).label('lon')
            ).limit(1)
        )
        hospital = result.first()
        if hospital:
            print(f"Sample Hospital: {hospital.name} at {hospital.lat}, {hospital.lon}")


if __name__ == "__main__":
    asyncio.run(check())
