# Database Setup and Testing Guide

## Quick Start

### 1. Install Dependencies

```bash
cd database
pip install -r requirements.txt
```

### 2. Set Environment Variable

```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/navigation_app"

# Windows CMD
set DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/navigation_app

# Linux/Mac
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/navigation_app"
```

Or create a `.env` file in the project root:
```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/navigation_app
```

### 3. Create Database and Run Schema

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE navigation_app;

# Connect to database
\c navigation_app

# Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# Exit psql
\q

# Run schema
psql -U postgres -d navigation_app -f database/schema.sql
```

### 4. Import Data

```bash
cd database
python import_data.py
```

This will:
- Import speed cameras from `tn_complete_cameras_detailed.json`
- Import speed limits from `chennai_speed_limit.json`
- Show progress and counts

### 5. Test Connection

```bash
cd database
python test_connection.py
```

This will:
- Test database health
- Count records in each table
- Test spatial queries near Chennai
- Verify everything is working

### 6. Start FastAPI Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8020
```

### 7. Test API Endpoints

```bash
# Health check
curl http://localhost:8020/health

# Get cameras near Chennai
curl "http://localhost:8020/api/cameras/nearby?latitude=13.0827&longitude=80.2707&radius_meters=5000"

# Get speed limits near Chennai
curl "http://localhost:8020/api/speed-limits/nearby?latitude=13.0827&longitude=80.2707&radius_meters=2000"

# Get all navigation data
curl "http://localhost:8020/api/navigation/nearby?latitude=13.0827&longitude=80.2707&radius_meters=5000"

# Count cameras
curl http://localhost:8020/api/cameras/count

# Count speed limits
curl http://localhost:8020/api/speed-limits/count
```

## Troubleshooting

### Database Connection Error

1. Check PostgreSQL is running:
   ```bash
   # Windows
   Get-Service postgresql*
   
   # Linux
   sudo systemctl status postgresql
   ```

2. Verify DATABASE_URL is correct:
   - Format: `postgresql+asyncpg://user:password@host:port/database`
   - Check username, password, host, port, and database name

3. Check PostgreSQL allows connections:
   - Edit `pg_hba.conf` if needed
   - Check firewall settings

### PostGIS Extension Error

```sql
-- Connect to database
\c navigation_app

-- Check if PostGIS is installed
SELECT PostGIS_version();

-- If not installed, install it:
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Import Errors

- Check JSON files exist in the `database` folder
- Verify JSON format is correct
- Check database has enough space
- Look for error messages in the import output

### Spatial Query Errors

- Verify PostGIS extension is enabled
- Check GiST indexes are created (they should be created by schema.sql)
- Verify coordinates are valid (lat: -90 to 90, lon: -180 to 180)

## Verification Checklist

- [ ] PostgreSQL 15+ installed
- [ ] PostGIS extension enabled
- [ ] Database created (`navigation_app`)
- [ ] Schema applied (`schema.sql`)
- [ ] Data imported (cameras and speed limits)
- [ ] Test script passes (`test_connection.py`)
- [ ] FastAPI backend starts without errors
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Camera endpoint returns data
- [ ] Speed limit endpoint returns data

## Next Steps

1. Update Flutter app to use the new API endpoints
2. Replace mock services with real API calls
3. Add authentication if needed
4. Set up production database with proper security
5. Add database backups
