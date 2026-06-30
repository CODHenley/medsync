-- ══════════════════════════════════════════════════════════════
-- ndc_product_map — learned NDC → product mappings
-- Run in: Supabase Dashboard → SQL Editor
-- ══════════════════════════════════════════════════════════════

create table if not exists public.ndc_product_map (
  id           uuid primary key default gen_random_uuid(),
  ndc          text not null unique,          -- scanned NDC or barcode value
  product_id   text,                          -- matches po_items.product_id
  product_name text not null,
  vendor       text,
  created_by   text,                          -- email of receiver who confirmed
  use_count    integer default 1,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

create index if not exists ndc_product_map_ndc_idx on public.ndc_product_map(ndc);

alter table public.ndc_product_map enable row level security;

create policy "anon select ndc_product_map"
  on public.ndc_product_map for select using (true);

create policy "anon insert ndc_product_map"
  on public.ndc_product_map for insert with check (true);

create policy "anon update ndc_product_map"
  on public.ndc_product_map for update using (true);
