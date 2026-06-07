-- ══════════════════════════════════════════════════════════════
-- MedSync — Purchase Order Queue Tables
-- Run this in Supabase SQL Editor (medsync project)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS po_items (
  id            uuid          DEFAULT gen_random_uuid() PRIMARY KEY,
  location_id   uuid          REFERENCES locations(id),
  product_id    uuid,                               -- nullable (manual adds may not have a DB product)
  product_name  text          NOT NULL,
  vendor        text          NOT NULL DEFAULT 'MWI Animal Health',
  qty_ordered   integer       NOT NULL DEFAULT 1,
  unit_price    numeric(10,2) DEFAULT 0,
  gpo_price     numeric(10,2) DEFAULT 0,
  on_hand       numeric(10,2) DEFAULT 0,
  week_start    date          NOT NULL,             -- Monday of the order week
  status        text          NOT NULL DEFAULT 'queued', -- queued | submitted | removed
  auto_flagged  boolean       DEFAULT false,        -- true = system added (below min), false = manual
  note          text,
  added_at      timestamptz   DEFAULT now()
);

-- Index for fast weekly queue lookups
CREATE INDEX IF NOT EXISTS po_items_location_week
  ON po_items (location_id, week_start, status);

-- Row Level Security (permissive — tighten later per role)
ALTER TABLE po_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "po_items_allow_all"
  ON po_items FOR ALL
  USING (true)
  WITH CHECK (true);
