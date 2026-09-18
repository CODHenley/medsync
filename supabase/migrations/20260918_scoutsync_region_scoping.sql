-- ══════════════════════════════════════════════════════════════════════════
-- ScoutSync region/hospital-scoped Admin access -- real, database-enforced
-- boundary (not a client-side filter): an Admin assigned to a region or a
-- specific set of hospitals genuinely cannot pull another hospital's data,
-- even via a direct API call with their own valid token.
--
-- This was applied live in the Supabase SQL editor in stages while chasing
-- a performance regression it introduced; this file captures the final,
-- correct end state in one place rather than the buggy intermediates.
-- Safe/idempotent to run again: ADD COLUMN IF NOT EXISTS, CREATE OR REPLACE
-- FUNCTION, and DROP POLICY IF EXISTS before each CREATE POLICY.
--
-- Performance note (the regression this migration's earlier attempts hit):
-- a plain USING (public.scoutsync_allowed_locations() IS NULL OR location_id
-- = ANY (public.scoutsync_allowed_locations())) calls the function once PER
-- ROW scanned -- confirmed via EXPLAIN ANALYZE showing "Rows Removed by
-- Filter: 42145" on appointment_events, ~1.9s just for that, which under
-- concurrent requests (the dashboard's parallel-pagination fetch) compounded
-- into multi-second timeouts. Wrapping the call in (SELECT ...) lets
-- Postgres hoist it into a single InitPlan/hashed SubPlan instead of
-- re-evaluating it per row -- confirmed via EXPLAIN ANALYZE showing
-- "InitPlan 1" / "hashed SubPlan 2", both loops=1, and execution time
-- dropping from ~1.9s to ~17ms for the same query. The `= ANY (SELECT
-- unnest(...))` shape (rather than the more obvious-looking
-- `= ANY ((SELECT ...))`) is required because `x = ANY (subquery)` in
-- Postgres expects the subquery to return ROWS of x's own type -- wrapping
-- a function that returns a single uuid[] value in a bare (SELECT ...)
-- makes it one row containing an array, not rows of uuid, and errors with
-- "operator does not exist: uuid = uuid[]". unnest() turns that one row's
-- array into the several plain-uuid rows the ANY(subquery) form actually
-- expects.
-- ══════════════════════════════════════════════════════════════════════════

BEGIN;

-- Descriptive job title, separate from the `role` column that actually
-- controls ScoutSync access (Hospital Director / Lead Doctor / Regional
-- Medical Director / Regional Hospital Director, etc.) -- purely cosmetic.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS title text;

-- Returns the set of location ids the CURRENT authenticated user is allowed
-- to see, based on their own row in public.users:
--   - medsync_superadmin, or access_scope = 'all'  -> NULL (sentinel for
--     "unrestricted" -- also the only case that can see rows where
--     location_id itself is NULL, e.g. corporate/unattributed records)
--   - access_scope = 'region'                       -> every location in
--     their assigned region
--   - access_scope = 'locations'                    -> exactly their
--     assigned location id list
--   - no matching user row, or anything else unrecognized -> empty array
--     (deny by default -- fails closed, never open)
CREATE OR REPLACE FUNCTION public.scoutsync_allowed_locations()
RETURNS uuid[]
LANGUAGE sql
STABLE
AS $$
  SELECT CASE
    WHEN u.role IS NULL THEN ARRAY[]::uuid[]
    WHEN u.role = 'medsync_superadmin' OR u.access_scope = 'all' THEN NULL
    WHEN u.access_scope = 'region' THEN (
      SELECT array_agg(l.id) FROM public.locations l WHERE l.region_id = u.access_region_id
    )
    WHEN u.access_scope = 'locations' THEN COALESCE(u.access_location_ids, ARRAY[]::uuid[])
    ELSE ARRAY[]::uuid[]
  END
  FROM (SELECT 1) d
  LEFT JOIN public.users u ON u.id = auth.uid();
$$;

-- Swap the blanket "see everything" policy for a scope-aware one on every
-- table that's actually tied to a specific hospital. Reference/shared data
-- (providers, product_categories, revenue_centers, regions, users itself,
-- etc.) is intentionally left untouched -- only hospital-specific
-- operational/financial/clinical rows are restricted. Branches on the
-- column's actual data type: most of these tables have a uuid location_id,
-- but 5 legacy tables (daily_revenue, dispensed_items, pending_receipts,
-- physical_count_sessions, product_locations) store it as text holding the
-- same location uuid as a string.
DO $$
DECLARE
  t text;
  col_type text;
  tables text[] := ARRAY[
    'activity_log','appointment_events','clients','daily_revenue','dispensed_items',
    'encounter_diagnostics','encounters','goods_lost','invoice_line_items','lots',
    'orders','pending_receipts','physical_count_sessions','po_items','price_review_flags',
    'product_locations','provider_shifts','purchase_history','received_invoices',
    'receiving_sessions'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    SELECT data_type INTO col_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = t AND column_name = 'location_id';

    IF col_type IS NULL THEN
      CONTINUE;
    END IF;

    EXECUTE format('DROP POLICY IF EXISTS "authenticated_all" ON public.%I', t);

    IF col_type = 'uuid' THEN
      EXECUTE format(
        'CREATE POLICY "authenticated_all" ON public.%I FOR ALL TO authenticated USING ((SELECT public.scoutsync_allowed_locations()) IS NULL OR location_id = ANY (SELECT unnest(public.scoutsync_allowed_locations()))) WITH CHECK ((SELECT public.scoutsync_allowed_locations()) IS NULL OR location_id = ANY (SELECT unnest(public.scoutsync_allowed_locations())))',
        t
      );
    ELSE
      -- location_id is text on this table but holds the same location uuid
      -- as a string -- cast the unnested elements to text instead of the
      -- column to uuid, since we can't guarantee every row is a clean uuid.
      EXECUTE format(
        'CREATE POLICY "authenticated_all" ON public.%I FOR ALL TO authenticated USING ((SELECT public.scoutsync_allowed_locations()) IS NULL OR location_id = ANY (SELECT unnest(public.scoutsync_allowed_locations())::text)) WITH CHECK ((SELECT public.scoutsync_allowed_locations()) IS NULL OR location_id = ANY (SELECT unnest(public.scoutsync_allowed_locations())::text))',
        t
      );
    END IF;
  END LOOP;
END $$;

COMMIT;
