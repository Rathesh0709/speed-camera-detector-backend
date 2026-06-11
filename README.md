# Speed Camera Detector — Backend

Backend for a driving-assistant system that combines **real-time speed-camera / hazard
detection** (computer vision) with a **geospatial database of speed cameras and speed
limits across Indian cities**. This is the server-side counterpart to the `zyra`
navigation app.

## Components

### `backend/` — FastAPI inference server
- **FastAPI + Uvicorn/Gunicorn** API.
- **YOLOv8** (`yolov8s.pt`, Ultralytics) for detecting speed cameras / road hazards from
  the camera feed.
- Auth (`bcrypt`, `python-jose` JWT), served with OpenCV (headless).
- Entry point: `backend/main.py`; containerized via `backend/Dockerfile`.

### `database/` — Speed-camera & speed-limit geospatial DB
- **PostgreSQL + PostGIS** accessed through **SQLAlchemy (async)**, `asyncpg`, and
  `GeoAlchemy2`.
- Bulk camera datasets for many Indian cities/states, e.g. **Chennai, Bengaluru, Delhi,
  Hyderabad, Coimbatore, Chandigarh, Dehradun, and Kerala (multiple regions)** — stored
  as `*_complete_cameras_detailed.json`.
- Additional layers: **speed limits** (`chennai_speed_limit.json`) and **hospital zones**
  (`hospital_zones.json`).
- Import/utility scripts: `bulk_import_cameras.py`, `import_data.py`, `import_zones.py`,
  `check_db.py`, `check_setup.py`, `example_usage.py`, plus `database.py`, `helpers.py`.
- See `database/INTEGRATION_SUMMARY.md` for integration notes.

## Tech stack

- **API/ML:** FastAPI, Uvicorn, Gunicorn, Ultralytics YOLOv8, OpenCV (headless), NumPy
- **Database:** PostgreSQL + PostGIS, SQLAlchemy (async) + asyncpg + GeoAlchemy2,
  Pydantic
- **Auth:** bcrypt, python-jose

## Getting started

### Database
```bash
cd database
cp .env.example .env          # set your PostgreSQL/PostGIS connection
pip install -r requirements.txt   # (root requirements.txt also covers backend deps)
python check_setup.py
python bulk_import_cameras.py      # import camera datasets
python import_zones.py             # import hospital zones
```

### Backend API
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
# or build the container:
docker build -t speed-camera-backend backend/
```

> Configure the database connection and any secrets via the `.env` files before running.
