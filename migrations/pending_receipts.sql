-- Stores unmatched items scanned during receiving that need admin resolution.
-- Admin either enables the existing product in VetSpire (next sync picks it up)
-- or adds it as new. Once resolved, product_id is linked and status → 'resolved'.

CREATE TABLE IF NOT EXISTS pending_receipts (
  id                uuid        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  scanned_value     text,                        -- NDC / barcode that was scanned
  fda_brand_name    text,
  fda_generic_name  text,
  fda_labeler       text,
  qty_received      integer,
  lot_number        text,
  expiry            text,                        -- MM/YYYY string as entered
  unit_cost         numeric(10,4),
  notes             text,
  po_ref            text,
  location_id       text,
  location_name     text,
  receiver_name     text,
  receiver_email    text,
  reported_at       timestamptz NOT NULL DEFAULT now(),
  status            text        NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','resolved','dismissed')),
  resolved_at       timestamptz,
  resolved_by       text,
  product_id        uuid        REFERENCES products(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pending_receipts_status   ON pending_receipts (status);
CREATE INDEX IF NOT EXISTS idx_pending_receipts_location ON pending_receipts (location_id);
CREATE INDEX IF NOT EXISTS idx_pending_receipts_reported ON pending_receipts (reported_at DESC);

ALTER TABLE pending_receipts ENABLE ROW LEVEL SECURITY;

-- Service role has full access (edge functions, python scripts)
CREATE POLICY "service role full access" ON pending_receipts
  FOR ALL USING (auth.role() = 'service_role');

-- Authenticated users can insert and read their own location's rows
CREATE POLICY "authenticated insert" ON pending_receipts
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "authenticated read" ON pending_receipts
  FOR SELECT USING (auth.role() = 'authenticated');
