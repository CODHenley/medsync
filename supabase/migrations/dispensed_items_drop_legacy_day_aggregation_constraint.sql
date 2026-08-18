-- The table still carried a UNIQUE(vetspire_product_id, dispensed_at, location_id)
-- constraint from the original day-aggregation design. It silently rejects any
-- legitimate insert of two distinct real Vetspire order items that share the
-- same product/location/timestamp — exactly the case the order_item_id-as-
-- sole-key fix (see dispensed_items_order_item_id_sole_key.sql) exists to
-- allow. As long as this constraint exists, a full per-item backfill can
-- never complete: every such collision is rejected with HTTP 409, leaving
-- Supabase's dispensed_items permanently short of Vetspire's real total.
--
-- order_item_id + location_id is now the only uniqueness Postgres should
-- enforce on this table (see the earlier migration). Drop the stale one.
alter table public.dispensed_items
  drop constraint if exists dispensed_items_vetspire_product_id_dispensed_at_location_i_key;
