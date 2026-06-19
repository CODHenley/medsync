-- Add unit_cost column to inventory_snapshots
-- Run once in Supabase SQL Editor
ALTER TABLE inventory_snapshots
  ADD COLUMN IF NOT EXISTS unit_cost numeric;
