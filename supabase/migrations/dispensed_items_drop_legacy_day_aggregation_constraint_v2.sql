-- The previous migration (dispensed_items_drop_legacy_day_aggregation_constraint.sql)
-- hand-typed a truncated constraint name transcribed from a garbled HTTP 409
-- error log and was off by one character, so its `drop constraint if exists`
-- silently no-op'd — confirmed by re-running the full-history backfill,
-- which hit the identical HTTP 409 on the identical constraint afterward.
--
-- This looks the object up by its actual column definition instead of a
-- guessed name, so it can't miss regardless of how Postgres's 63-byte
-- identifier truncation mangled it. Handles both a real UNIQUE CONSTRAINT
-- and a plain UNIQUE INDEX not backed by one.
--
-- order_item_id + location_id is now the only uniqueness Postgres should
-- enforce on this table (see dispensed_items_order_item_id_sole_key.sql).
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
