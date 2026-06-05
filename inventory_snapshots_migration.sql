-- MedSync — inventory_snapshots table
-- Run once in Supabase SQL Editor before first daily sync.
-- Stores daily on-hand readings pulled from Vetspire at midnight.

CREATE TABLE IF NOT EXISTS inventory_snapshots (
  id                    uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  vetspire_location_id  text NOT NULL,
  location_name         text NOT NULL,
  vetspire_product_id   text NOT NULL,
  product_name          text NOT NULL,
  on_hand               numeric NOT NULL,
  snapshot_date         date NOT NULL DEFAULT CURRENT_DATE,
  created_at            timestamptz DEFAULT NOW()
);

-- Unique constraint: one snapshot per product per location per day
CREATE UNIQUE INDEX IF NOT EXISTS inventory_snapshots_unique_daily
  ON inventory_snapshots (vetspire_location_id, vetspire_product_id, snapshot_date);

-- Index for history lookups (location + product + date range)
CREATE INDEX IF NOT EXISTS inventory_snapshots_lookup
  ON inventory_snapshots (vetspire_location_id, vetspire_product_id, snapshot_date DESC);

-- Open read/write for the anon key (same RLS pattern as other tables)
ALTER TABLE inventory_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon read"   ON inventory_snapshots FOR SELECT USING (true);
CREATE POLICY "anon insert" ON inventory_snapshots FOR INSERT WITH CHECK (true);
CREATE POLICY "anon update" ON inventory_snapshots FOR UPDATE USING (true);

-- Handy view: 30-day average daily consumption per product per location
-- (only counts usage days — ignores restock days where on_hand went UP)
CREATE OR REPLACE VIEW daily_consumption_30d AS
SELECT
  vetspire_location_id,
  location_name,
  vetspire_product_id,
  product_name,
  COUNT(*)                   AS days_of_data,
  ROUND(AVG(daily_delta), 2) AS avg_daily_usage,
  MAX(snapshot_date)         AS latest_snapshot
FROM (
  SELECT
    vetspire_location_id,
    location_name,
    vetspire_product_id,
    product_name,
    snapshot_date,
    on_hand,
    LAG(on_hand) OVER (
      PARTITION BY vetspire_location_id, vetspire_product_id
      ORDER BY snapshot_date
    ) - on_hand AS daily_delta
  FROM inventory_snapshots
  WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
) sub
WHERE daily_delta > 0   -- only count days stock went DOWN (usage, not restock)
GROUP BY
  vetspire_location_id,
  location_name,
  vetspire_product_id,
  product_name;
