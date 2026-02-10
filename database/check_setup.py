"""
Quick setup checker for database configuration.
Run this before importing data to verify your setup.
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("Database Setup Checker")
print("=" * 60)

# Check 1: DATABASE_URL
print("\n1. Checking DATABASE_URL environment variable...")
database_url = os.getenv("DATABASE_URL")
if database_url:
    print(f"   ✓ DATABASE_URL is set")
    # Mask password in output
    if "@" in database_url:
        parts = database_url.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                masked_url = database_url.replace(f":{user_pass.split(':')[1]}", ":****")
                print(f"   URL: {masked_url}")
    else:
        print(f"   URL: {database_url}")
else:
    print("   ✗ DATABASE_URL is NOT set")
    print("\n   Please set it using:")
    print("   Windows PowerShell:")
    print('     $env:DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"')
    print("   Windows CMD:")
    print('     set DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app')
    sys.exit(1)

# Check 2: JSON files
print("\n2. Checking data files...")
script_dir = Path(__file__).parent
cameras_file = script_dir / "tn_complete_cameras_detailed.json"
speed_limits_file = script_dir / "chennai_speed_limit.json"

if cameras_file.exists():
    print(f"   ✓ Speed cameras file found: {cameras_file.name}")
else:
    print(f"   ✗ Speed cameras file NOT found: {cameras_file.name}")

if speed_limits_file.exists():
    print(f"   ✓ Speed limits file found: {speed_limits_file.name}")
else:
    print(f"   ✗ Speed limits file NOT found: {speed_limits_file.name}")

# Check 3: Test database connection
print("\n3. Testing database connection...")
try:
    import asyncio
    from database.database import check_db_health, AsyncSessionLocal
    from sqlalchemy import text
    
    async def test_connection():
        try:
            is_healthy = await check_db_health()
            if is_healthy:
                print("   ✓ Database connection successful!")
                
                # Try to check if database exists and has tables
                try:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                        )
                        table_count = result.scalar()
                        print(f"   ✓ Found {table_count} tables in database")
                except Exception as e:
                    print(f"   ⚠ Could not check tables: {e}")
                
                return True
            else:
                print("   ✗ Database connection failed!")
                print("\n   Possible issues:")
                print("   - PostgreSQL is not running")
                print("   - Wrong password in DATABASE_URL")
                print("   - Database 'navigation_app' does not exist")
                print("   - PostgreSQL is not listening on the expected port")
                return False
        except Exception as e:
            print(f"   ✗ Connection error: {e}")
            print("\n   Possible issues:")
            print("   - PostgreSQL is not running")
            print("   - Wrong password in DATABASE_URL")
            print("   - Database 'navigation_app' does not exist")
            return False
    
    result = asyncio.run(test_connection())
    if not result:
        sys.exit(1)
        
except ImportError as e:
    print(f"   ✗ Error importing database modules: {e}")
    print("\n   Please install dependencies:")
    print("     pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Connection error: {e}")
    print("\n   Please check:")
    print("   - PostgreSQL is running")
    print("   - DATABASE_URL is correct")
    print("   - Database 'navigation_app' exists")
    sys.exit(1)

# Check 4: PostGIS extension
print("\n4. Checking PostGIS extension...")
try:
    import asyncio
    from database.database import AsyncSessionLocal
    from sqlalchemy import text
    
    async def check_postgis():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
            )
            has_postgis = result.scalar()
            if has_postgis:
                print("   ✓ PostGIS extension is enabled")
                return True
            else:
                print("   ✗ PostGIS extension is NOT enabled")
                print("\n   Please run in psql:")
                print("     CREATE EXTENSION IF NOT EXISTS postgis;")
                return False
    
    if not asyncio.run(check_postgis()):
        sys.exit(1)
        
except Exception as e:
    print(f"   ⚠ Could not check PostGIS: {e}")

print("\n" + "=" * 60)
print("✓ Setup check complete! You can now run:")
print("  python import_data.py")
print("=" * 60)
