-- ══════════════════════════════════════════════════════════════
-- MedSync — Unreceived PO Flagging Migration
-- Task #28: Flag POs placed but not received within 3 days
-- Run in Supabase SQL Editor (medsync project)
-- ══════════════════════════════════════════════════════════════

-- Add submitted_at timestamp to po_items
-- Tracks when a PO was actually sent to the vendor (vs. added_at which is when it was queued)
ALTER TABLE po_items
  ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ DEFAULT NULL;

-- Backfill: for existing submitted/received items, use added_at as best estimate
UPDATE po_items
  SET submitted_at = added_at
  WHERE status IN ('submitted', 'received')
    AND submitted_at IS NULL;

-- Index for fast overdue queries
CREATE INDEX IF NOT EXISTS po_items_submitted_at
  ON po_items (submitted_at)
  WHERE status = 'submitted';
