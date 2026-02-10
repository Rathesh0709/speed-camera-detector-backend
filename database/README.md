# Navigation App Database Schema

PostgreSQL + PostGIS database schema and async SQLAlchemy models for the Flutter Navigation App backend.

## Requirements

- PostgreSQL 15+
- PostGIS extension
- Python 3.10+
- Dependencies listed in `requirements.txt`

## Setup

### 1. Install PostgreSQL with PostGIS

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-15-postgis-3

# macOS (Homebrew)
brew install postgresql@15 postgis

# Windows: Download from postgresql.org and install PostGIS extension
```

### 2. Create Database

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE navigation_app;

-- Connect to the database
\c navigation_app

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 3. Run Schema

```bash
# Apply the schema
psql -U postgres -d navigation_app -f schema.sql
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

Set the `DATABASE_URL` environment variable:

```bash
# Format: postgresql+asyncpg://user:password@host:port/database
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/navigation_app"
```

Or create a `.env` file:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/navigation_app
DB_ECHO=false  # Set to true for SQL query logging
```

## Database Schema

### Tables

1. **users** - User accounts
2. **speed_cameras** - Speed camera locations (Point geometry)
3. **road_speed_limits** - Road speed limit segments (LineString geometry)
4. **hazard_detections** - Hazard detections (Point geometry)
5. **user_camera_reports** - User reports for cameras
6. **user_speed_limit_reports** - User reports for speed limits

### Key Features

- **UUID primary keys** for all tables
- **PostGIS GEOGRAPHY** (SRID 4326) for spatial data
- **GiST indexes** on all geometry columns for fast spatial queries
- **Confidence scores** (0.0 to 1.0) for user-generated data
- **Verification system** with automatic verification after threshold reports
- **Foreign keys** with proper CASCADE/SET NULL behavior

## Usage

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, init_db, close_db
from database.queries import get_nearby_speed_cameras

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

@app.get("/cameras")
async def get_cameras(
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_db)
):
    cameras = await get_nearby_speed_cameras(
        db=db,
        latitude=lat,
        longitude=lon,
        radius_meters=1000.0
    )
    return cameras
```

### Example Queries

See `queries.py` for example functions:

- `get_nearby_speed_cameras()` - Find cameras near a point
- `get_nearby_speed_limits()` - Find speed limits near a point
- `get_nearby_hazards()` - Find hazards near a point
- `get_speed_cameras_along_route()` - Find cameras along a route
- `get_speed_limits_along_route()` - Find speed limits along a route
- `create_speed_camera()` - Create a new camera record
- `create_road_speed_limit()` - Create a new speed limit record

### Models

All models are in `models.py`:

- `User`
- `SpeedCamera`
- `RoadSpeedLimit`
- `HazardDetection`
- `UserCameraReport`
- `UserSpeedLimitReport`

## Spatial Queries

The database uses PostGIS GEOGRAPHY type (SRID 4326) for all spatial data. This provides:

- Accurate distance calculations on Earth's surface
- Support for lat/lon coordinates directly
- Efficient spatial indexing with GiST

Example spatial query:

```python
# Find cameras within 1km of a point
cameras = await get_nearby_speed_cameras(
    db=db,
    latitude=37.7749,
    longitude=-122.4194,
    radius_meters=1000.0
)
```

## Verification System

The database includes automatic verification triggers:

- After 5+ user confirmations with 80%+ confirmation rate, cameras/speed limits are auto-verified
- Verified records are marked with `verified = TRUE`
- Verification count is tracked

## Indexes

All spatial columns have GiST indexes for fast spatial queries:

- `speed_cameras.location`
- `road_speed_limits.road_segment`
- `hazard_detections.location`

Additional indexes on:
- Foreign keys
- Confidence scores
- Verification flags
- Timestamps
- Common query fields

## Notes

- All timestamps use `TIMESTAMP WITH TIME ZONE`
- UUIDs are generated automatically using `uuid_generate_v4()`
- `updated_at` is automatically maintained by triggers
- Confidence scores are constrained to 0.0-1.0 range

## Testing

```python
# Test database connection
from database import check_db_health

is_healthy = await check_db_health()
print(f"Database healthy: {is_healthy}")
```

## Migration

For production, consider using Alembic for database migrations:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini with your DATABASE_URL
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```
