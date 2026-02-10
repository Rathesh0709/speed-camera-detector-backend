# Quick Start Guide

## Step 1: Set Database Password

You need to set the `DATABASE_URL` environment variable with your PostgreSQL password.

### Windows PowerShell:
```powershell
$env:DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"
```

### Windows CMD:
```cmd
set DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app
```

### Linux/Mac:
```bash
export DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/navigation_app"
```

**Replace `YOUR_PASSWORD` with your actual PostgreSQL password!**

If you don't know your PostgreSQL password:
- Check if you set it during installation
- Try common defaults: `postgres`, `admin`, `password`, or empty string `""`
- Reset it in PostgreSQL if needed

## Step 2: Verify Setup

Run the setup checker to verify everything is configured correctly:

```bash
cd database
python check_setup.py
```

This will check:
- ✓ DATABASE_URL is set
- ✓ Data files exist
- ✓ Database connection works
- ✓ PostGIS extension is enabled

## Step 3: Create Database (if not exists)

If the database doesn't exist yet:

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

# Exit
\q
```

## Step 4: Run Schema (if not done)

```bash
psql -U postgres -d navigation_app -f database/schema.sql
```

## Step 5: Import Data

```bash
cd database
python import_data.py
```

## Troubleshooting

### "password authentication failed"
- Your DATABASE_URL password is incorrect
- Check your PostgreSQL password and update DATABASE_URL

### "database does not exist"
- Create the database: `CREATE DATABASE navigation_app;`

### "extension postgis does not exist"
- Install PostGIS extension: `CREATE EXTENSION IF NOT EXISTS postgis;`

### "DATABASE_URL is not set"
- Set the environment variable (see Step 1 above)
- Make sure to set it in the same terminal session where you run the scripts

## Need Help?

Run the setup checker for detailed diagnostics:
```bash
python check_setup.py
```
