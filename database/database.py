"""
Async database connection setup for FastAPI with PostgreSQL + PostGIS.
Requires: asyncpg, sqlalchemy[asyncio]
"""

import os
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .models import Base

# Database URL from environment variable
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()
    # Check if the URL includes a database name
    # We look for a slash after the host:port part
    from urllib.parse import urlparse, urlunparse
    try:
        parsed = urlparse(DATABASE_URL)
        if not parsed.path or parsed.path == '/':
            # No database name specified, default to navigation_app
            new_path = "/navigation_app"
            parsed = parsed._replace(path=new_path)
            DATABASE_URL = urlunparse(parsed)
            print(f"DEBUG: No database name in URL, using default: {DATABASE_URL}")
    except Exception as e:
        print(f"DEBUG: Error parsing DATABASE_URL: {e}")

if not DATABASE_URL:
    print("=" * 60)
    print("ERROR: DATABASE_URL environment variable is not set!")
    print("=" * 60)
    print("\nPlease set the DATABASE_URL environment variable:")
    print("\n  Windows PowerShell:")
    print('    $env:DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"')
    print("\n  Windows CMD:")
    print('    set DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app')
    print("\n  Linux/Mac:")
    print('    export DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"')
    print("\nOr create a .env file in the project root with:")
    print("  DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app")
    print("\nReplace YOUR_PASSWORD with your actual PostgreSQL password.")
    print("=" * 60)
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Please set it with your PostgreSQL connection string."
    )

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",  # Set DB_ECHO=true for SQL logging
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to get database session.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - create all tables.
    Call this once at application startup.
    
    Usage:
        @app.on_event("startup")
        async def startup():
            await init_db()
    """
    async with engine.begin() as conn:
        # Ensure PostGIS extension exists so GeoAlchemy geography types work.
        # This is safe to run multiple times.
        try:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
        except Exception as exc:
            # Log a clear message but don't swallow the error silently.
            print("=" * 60)
            print("ERROR: Failed to create PostGIS extension.")
            print(
                "Make sure PostGIS is installed in your PostgreSQL instance.\n"
                "On Windows with PostgreSQL App/StackBuilder, add the PostGIS extension\n"
                "to your server, then re-run the backend."
            )
            print(f"Underlying error: {exc}")
            print("=" * 60)
            raise

        # Create all tables after PostGIS extension is available.
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Call this at application shutdown.
    
    Usage:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db()
    """
    await engine.dispose()


# Health check function
async def check_db_health() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False
