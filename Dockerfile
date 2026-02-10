# Use Python 3.10 slim image
FROM python:3.10-slim

# Install system dependencies for OpenCV and PostGIS client
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend files to the root of /app
# This ensures paths like 'models/best.pt' and 'yolov8s.pt' work correctly
COPY backend/ .
COPY database/ ./database/

# Create static directory for uploads
RUN mkdir -p static/hazards

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8020

# Start with Gunicorn/Uvicorn
# Note: Using 'main:app' because main.py is now in the root
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8020"]
