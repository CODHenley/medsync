-- MedSync Missing Tables Migration
-- Run in Supabase SQL Editor (safe to run multiple times — all use IF NOT EXISTS)
-- Generated: 2026-06-07

-- ─────────────────────────────────────────────────────────────────
-- 1. LOTS
--    Created by IL Receiving and Hospital Receiver on PO completion.
--    Read by Lot Lifecycle screen and Weekly Order (qty_remaining).
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.lots (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id       UUID REFERENCES public.products(id) ON DELETE SET NULL,
  location_id      UUID REFERENCES public.locations(id) ON DELETE CASCADE,
  lot_number       TEXT,
  qty_received     INTEGER NOT NULL DEFAULT 0,
  qty_remaining    INTEGER NOT NULL DEFAULT 0,
  received_date    DATE,
  expiration_date  DATE,
  status           TEXT NOT NULL DEFAULT 'Active'
                   CHECK (status IN ('Active','Expiring Soon','Expired','Disposed')),
  po_reference     TEXT,
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.lots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "lots_all" ON public.lots FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS lots_location_id_idx ON public.lots(location_id);
CREATE INDEX IF NOT EXISTS lots_expiration_date_idx ON public.lots(expiration_date);
CREATE INDEX IF NOT EXISTS lots_status_idx ON public.lots(status);


-- ─────────────────────────────────────────────────────────────────
-- 2. RECEIVING SESSIONS
--    Created by IL Receiving on PO completion (audit trail).
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.receiving_sessions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id      UUID REFERENCES public.locations(id) ON DELETE CASCADE,
  status           TEXT NOT NULL DEFAULT 'Completed'
                   CHECK (status IN ('Completed','Flagged','Partial')),
  skus_expected    INTEGER NOT NULL DEFAULT 0,
  skus_scanned     INTEGER NOT NULL DEFAULT 0,
  has_discrepancy  BOOLEAN NOT NULL DEFAULT FALSE,
  completed_at     TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.receiving_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "receiving_sessions_all" ON public.receiving_sessions FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS receiving_sessions_location_id_idx ON public.receiving_sessions(location_id);


-- ─────────────────────────────────────────────────────────────────
-- 3. ACTIVITY LOG
--    Written by all major workflows (receiving, goods lost, cycle
--    count, weekly order). Read by Activity Log screen and Lot
--    Lifecycle detail panel.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.activity_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id  UUID REFERENCES public.locations(id) ON DELETE SET NULL,
  user_id      UUID REFERENCES public.users(id) ON DELETE SET NULL,
  event_type   TEXT NOT NULL
               CHECK (event_type IN ('order','receive','goods','user','cycle','system')),
  description  TEXT NOT NULL,
  reference_id TEXT,
  flag         TEXT NOT NULL DEFAULT 'ok'
               CHECK (flag IN ('ok','warn','error')),
  detail       TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "activity_log_all" ON public.activity_log FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS activity_log_location_id_idx ON public.activity_log(location_id);
CREATE INDEX IF NOT EXISTS activity_log_created_at_idx ON public.activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS activity_log_event_type_idx ON public.activity_log(event_type);
CREATE INDEX IF NOT EXISTS activity_log_reference_id_idx ON public.activity_log(reference_id);


-- ─────────────────────────────────────────────────────────────────
-- 4. GOODS LOST
--    Written by Goods Lost screen and IL Receiving (discrepancy).
--    Read by Goods Lost history panel and Analytics.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.goods_lost (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id   UUID REFERENCES public.locations(id) ON DELETE CASCADE,
  product_id    UUID REFERENCES public.products(id) ON DELETE SET NULL,
  product_name  TEXT,
  category      TEXT NOT NULL,
  sub_category  TEXT,
  qty_lost      INTEGER NOT NULL DEFAULT 1,
  value_lost    NUMERIC(10,2) NOT NULL DEFAULT 0,
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.goods_lost ENABLE ROW LEVEL SECURITY;
CREATE POLICY "goods_lost_all" ON public.goods_lost FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS goods_lost_location_id_idx ON public.goods_lost(location_id);
CREATE INDEX IF NOT EXISTS goods_lost_created_at_idx ON public.goods_lost(created_at DESC);
