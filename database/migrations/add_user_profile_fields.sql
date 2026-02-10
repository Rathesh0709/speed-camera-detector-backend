-- Migration: Add profile_photo_url and trips_count to users table
-- Run this SQL script on your PostgreSQL database

ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trips_count INTEGER DEFAULT 0;

-- Update existing rows to have trips_count = 0 if NULL
UPDATE users SET trips_count = 0 WHERE trips_count IS NULL;
