-- MedSync: add is_active column to users table
-- Run in Supabase SQL Editor before deploying the updated users screen.

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;
UPDATE users SET is_active = true WHERE is_active IS NULL;
