-- ══════════════════════════════════════════════════════════════
-- received_invoices table + invoices Storage bucket
-- Run this in: Supabase Dashboard → SQL Editor → New query
-- ══════════════════════════════════════════════════════════════

-- 1. Table
create table if not exists public.received_invoices (
  id             uuid primary key default gen_random_uuid(),
  location_id    uuid references public.locations(id) on delete set null,
  session_id     uuid,                        -- FK to receiving_sessions (soft ref)
  vendor         text,
  po_reference   text,
  invoice_number text,
  invoice_date   date,
  received_date  date,
  received_by    text,                        -- email of the receiver
  total_amount   numeric(10,2),
  skus_count     integer,
  has_discrepancy boolean default false,
  invoice_url    text,                        -- Supabase Storage public URL
  notes          text,
  created_at     timestamptz default now()
);

-- Index for common queries
create index if not exists received_invoices_location_id_idx on public.received_invoices(location_id);
create index if not exists received_invoices_received_date_idx on public.received_invoices(received_date desc);
create index if not exists received_invoices_vendor_idx        on public.received_invoices(vendor);

-- 2. RLS — enable but allow anon read/write (same pattern as rest of app)
alter table public.received_invoices enable row level security;

create policy "anon select received_invoices"
  on public.received_invoices for select using (true);

create policy "anon insert received_invoices"
  on public.received_invoices for insert with check (true);

create policy "anon update received_invoices"
  on public.received_invoices for update using (true);

-- 3. Also add missing columns to receiving_sessions if they don't exist
--    (these were added to the INSERT in the receiving flow)
alter table public.receiving_sessions
  add column if not exists vendor        text,
  add column if not exists po_reference  text,
  add column if not exists received_by   text,
  add column if not exists invoice_date  date,
  add column if not exists received_date date,
  add column if not exists total_amount  numeric(10,2),
  add column if not exists invoice_url   text,
  add column if not exists notes         text;

-- ══════════════════════════════════════════════════════════════
-- Storage bucket — run AFTER the table above, in the same editor
-- ══════════════════════════════════════════════════════════════
insert into storage.buckets (id, name, public)
  values ('invoices', 'invoices', true)
  on conflict (id) do nothing;

-- Allow anon uploads and reads
create policy "anon upload invoices"
  on storage.objects for insert
  to anon
  with check (bucket_id = 'invoices');

create policy "anon read invoices"
  on storage.objects for select
  to anon
  using (bucket_id = 'invoices');

create policy "anon update invoices"
  on storage.objects for update
  to anon
  using (bucket_id = 'invoices');
