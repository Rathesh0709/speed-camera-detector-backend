# How to Start the FastAPI Backend

## Important: Run from the correct directory!

The FastAPI backend (`main.py`) is in the `backend` folder, not the `database` folder.

## Steps:

### 1. Navigate to the backend directory:
```bash
cd ..\backend
```

Or from the project root:
```bash
cd backend
```

### 2. Make sure DATABASE_URL is set:
```powershell
# Windows PowerShell
$env:DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"
```

### 3. Start the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8020
```

## Full Command Sequence:

```powershell
# Set database URL (if not already set)
$env:DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"

# Navigate to backend
cd ..\backend

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8020
```

## Verify it's working:

Once started, you should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8020 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Waiting for application startup.
✓ Database initialized
INFO:     Application startup complete.
```

## Test the API:

Open in browser or use curl:
- Health check: http://localhost:8020/health
- API docs: http://localhost:8020/docs
- Cameras: http://localhost:8020/api/cameras/nearby?latitude=13.0827&longitude=80.2707&radius_meters=5000

## Troubleshooting:

### "Could not import module 'main'"
- You're in the wrong directory. Make sure you're in the `backend` folder.

### "DATABASE_URL is not set"
- Set the environment variable before starting the server.

### "password authentication failed"
- Check your PostgreSQL password in DATABASE_URL.
