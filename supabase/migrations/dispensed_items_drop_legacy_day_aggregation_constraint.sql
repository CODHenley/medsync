-- The table still carried a UNIQUE(vetspire_product_id, dispensed_at, location_id)
-- constraint from the original day-aggregation design. It silently rejects any
-- legitimate insert of two distinct real Vetspire order items that share the
-- same product/location/timestamp — exactly the case the order_item_id-as-
-- sole-key fix (see dispensed_items_order_item_id_sole_key.sql) exists to
-- allow. As long as this constraint exists, a full per-item backfill can
-- never complete: every such collision is rejected with HTTP 409, leaving
-- Supabase's dispensed_items permanently short of Vetspire's real total.
--
-- A prior version of this migration dropped a hand-typed constraint name and
-- silently no-op'd — Postgres truncates auto-generated constraint names to
-- 63 bytes, and the truncated name was mistyped by one character from a
-- garbled error-log excerpt. This version looks the object up by its actual
-- definition instead of guessing its name, so it can't miss again — it
-- handles both a real UNIQUE CONSTRAINT and a plain UNIQUE INDEX not backed
-- by one.
--
-- order_item_id + location_id is now the only uniqueness Postgres should
-- enforce on this table (see the earlier migration).
do $$
declare
  rec record;
begin
  for rec in
    select conname as name
    from pg_constraint
    where conrelid = 'public.dispensed_items'::regclass
      and contype = 'u'
      and pg_get_constraintdef(oid) ilike '%vetspire_product_id%'
      and pg_get_constraintdef(oid) ilike '%dispensed_at%'
      and pg_get_constraintdef(oid) ilike '%location_id%'
  loop
    execute format('alter table public.dispensed_items drop constraint %I', rec.name);
    raise notice 'Dropped constraint %', rec.name;
  end loop;

  for rec in
    select indexname as name
    from pg_indexes
    where schemaname = 'public'
      and tablename = 'dispensed_items'
      and indexdef ilike '%unique%'
      and indexdef ilike '%vetspire_product_id%'
      and indexdef ilike '%dispensed_at%'
      and indexdef ilike '%location_id%'
  loop
    execute format('drop index if exists public.%I', rec.name);
    raise notice 'Dropped index %', rec.name;
  end loop;
end $$;
