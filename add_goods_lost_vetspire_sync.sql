-- MedSync — Add Vetspire sync tracking to goods_lost
-- Run once in: Supabase → SQL Editor → New Query → Paste → Run

-- 1. Add sync tracking columns to goods_lost
ALTER TABLE goods_lost
  ADD COLUMN IF NOT EXISTS vetspire_synced       BOOLEAN   DEFAULT FALSE NOT NULL,
  ADD COLUMN IF NOT EXISTS vetspire_synced_at    TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS vetspire_sync_error   TEXT;

-- 2. Index for the sync script (only fetches unsynced rows)
CREATE INDEX IF NOT EXISTS goods_lost_unsynced_idx
  ON goods_lost (vetspire_synced, created_at)
  WHERE vetspire_synced = FALSE;
