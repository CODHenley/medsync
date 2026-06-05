-- MedSync: add data access scope columns to users table
-- Run in Supabase SQL Editor

ALTER TABLE users ADD COLUMN IF NOT EXISTS access_scope text DEFAULT 'all';
ALTER TABLE users ADD COLUMN IF NOT EXISTS access_region_id uuid REFERENCES regions(id) ON DELETE SET NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS access_location_ids uuid[];

-- Default all existing users to full access
UPDATE users SET access_scope = 'all' WHERE access_scope IS NULL;
