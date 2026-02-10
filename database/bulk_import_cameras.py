
import asyncio
import os
import sys
from pathlib import Path

# Fix: Sanitize DATABASE_URL before importing modules that use it
if os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL").strip()
else:
    # Use user provided credentials + app database name
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:1634@localhost:5432/navigation_app"
    print(f"Using default DATABASE_URL: {os.environ['DATABASE_URL']}")

# Add parent directory to path to import database modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import AsyncSessionLocal, init_db
from database.import_data import import_speed_cameras, import_speed_limits

async def main():
    print("=" * 60)
    print("Bulk Import Speed Cameras")
    print("=" * 60)

    # Initialize DB
    print("\n1. Initializing database...")
    await init_db()
    
    # Scan for files
    db_dir = Path(__file__).parent
    json_files = list(db_dir.glob("*_complete_cameras_detailed.json"))
    
    print(f"\nFound {len(json_files)} camera data files.")
    
    total_cameras = 0
    
    async with AsyncSessionLocal() as db:
        for json_file in json_files:
            print(f"\nProcessing: {json_file.name}")
            try:
                count = await import_speed_cameras(db, str(json_file))
                total_cameras += count
            except Exception as e:
                print(f"Error processing {json_file.name}: {e}")

    print("\n" + "=" * 60)
    print(f"Bulk Import Complete! Total imported: {total_cameras}")
    print("=" * 60)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
