-- ══════════════════════════════════════════════════════════════
-- price_review_flags — IL-flagged unit cost discrepancies
-- Run in: Supabase Dashboard → SQL Editor
-- ══════════════════════════════════════════════════════════════

create table if not exists public.price_review_flags (
  id               uuid primary key default gen_random_uuid(),
  product_id       text,
  product_name     text not null,
  sku              text,
  vetspire_product_id text,
  location_id      uuid references public.locations(id) on delete set null,
  location_name    text,
  vetspire_cost    numeric(10,4),   -- unit cost currently in VetSpire
  invoice_cost     numeric(10,4),   -- unit price on the received invoice
  drift_pct        numeric(6,2),    -- ((invoice - vetspire) / vetspire) * 100
  po_reference     text,
  flagged_by       text,            -- email of IL who flagged
  flagged_at       timestamptz default now(),
  status           text not null default 'pending'
                     check (status in ('pending','approved_pending_sync','approved_synced','rejected','hold')),
  resolved_by      text,
  resolved_at      timestamptz,
  resolution_notes text,
  vetspire_synced  boolean default false,
  created_at       timestamptz default now()
);

create index if not exists price_review_flags_status_idx    on public.price_review_flags(status);
create index if not exists price_review_flags_location_idx  on public.price_review_flags(location_id);
create index if not exists price_review_flags_flagged_at_idx on public.price_review_flags(flagged_at desc);

alter table public.price_review_flags enable row level security;

create policy "anon select price_review_flags"
  on public.price_review_flags for select using (true);

create policy "anon insert price_review_flags"
  on public.price_review_flags for insert with check (true);

create policy "anon update price_review_flags"
  on public.price_review_flags for update using (true);
