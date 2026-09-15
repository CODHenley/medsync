-- ══════════════════════════════════════════════════════════════════════════
-- Revoke anon_all — closes the "anyone with the public anon key has full
-- read/write access to nearly the entire database" exposure.
--
-- Every legitimate access path has since moved off the anon key:
--   - All browser pages now require a real MedSync login and send the
--     signed-in user's own token (authenticated role).
--   - All backend sync/backfill scripts now prefer SUPA_SERVICE_KEY
--     (service_role, bypasses RLS entirely) over the anon key.
--
-- This migration:
--   1. Drops every anon-granting policy, not just ones literally named
--      "anon_all" -- several tables (price_review_flags, ndc_product_map,
--      received_invoices) also carry separately-named policies with no
--      "to <role>" clause, which defaults to PUBLIC (every role, anon
--      included) and would otherwise survive step 1 untouched.
--   2. Adds "authenticated_all" to every table that had its own anon_all
--      (created directly in that table's own migration, not through
--      20260812_enable_rls.sql / 20260820_add_authenticated_rls_policies.sql)
--      and therefore never got one -- without this, logged-in staff lose
--      access to that table the moment anon_all is gone.
--   3. Closes the "invoices" Storage bucket -- it was created fully public,
--      which serves files over a plain public URL with NO auth check at
--      all, not even the anon key. This is fixed regardless of anything
--      else here.
--   4. Sets security_invoker on every dashboard-supporting view. Without
--      it, a view can silently keep bypassing RLS on its own underlying
--      table (a well-known Postgres/Supabase default), which would make
--      steps 1-2 look like they worked while anon could still read
--      everything straight through the view.
--
-- KNOWN, ACCEPTED REGRESSION: medsync_unsubscribe.html's public, no-login
-- email-preferences link updates `users` using the anon key. After this
-- migration that flow fails closed (shows an error, points to Settings)
-- until it's rebuilt on a scoped, token-based policy -- not a bug.
--
-- Run this as one script in the Supabase SQL Editor. It's wrapped in a
-- single transaction: if anything in it fails, nothing is applied.
-- ══════════════════════════════════════════════════════════════════════════

BEGIN;

-- ── 1a. Tables covered by the original anon_all/authenticated_all pair --
--       authenticated_all already exists on every one of these; just drop
--       the anon policy. ──
DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'daily_revenue', 'purchase_history', 'locations', 'products', 'lots',
    'po_items', 'goods_lost', 'dispensed_items', 'cycle_counts',
    'inventory_snapshots', 'activity_log', 'price_review_flags',
    'ndc_product_map', 'receiving_sessions', 'invoices', 'invoice_items',
    'received_invoices', 'order_lines', 'purchase_orders', 'active_products',
    'physical_count_sessions', 'physical_count_items',
    'vetspire_writeback_queue', 'quiz_completions', 'messages',
    'message_reads', 'regions', 'location_settings', 'organization_settings',
    'billing_change_log', 'users', 'user_profiles', 'organizations'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = t AND table_type = 'BASE TABLE'
    ) THEN
      EXECUTE format('DROP POLICY IF EXISTS "anon_all" ON public.%I', t);
    END IF;
  END LOOP;
END $$;

-- ── 1b. Tables that got their OWN anon_all directly in their own creation
--       migration and were never added to authenticated_all -- drop anon,
--       add authenticated so logged-in access doesn't break. ──
DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'appointment_events', 'encounter_diagnostics', 'product_categories',
    'provider_shifts', 'rdvm_directory', 'rdvm_revenue_daily',
    'revenue_centers', 'zip_demographics', 'providers', 'clients',
    'patients', 'encounters', 'referral_relationships',
    'records_release_log', 'invoice_line_items'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = t AND table_type = 'BASE TABLE'
    ) THEN
      EXECUTE format('DROP POLICY IF EXISTS "anon_all" ON public.%I', t);
      EXECUTE format('DROP POLICY IF EXISTS "authenticated_all" ON public.%I', t); -- in case a later run added one already
      EXECUTE format(
        'CREATE POLICY "authenticated_all" ON public.%I FOR ALL TO authenticated USING (true) WITH CHECK (true)', t
      );
    END IF;
  END LOOP;
END $$;

-- ── 1c. Differently-named PUBLIC policies (no "to <role>" clause -- applies
--       to every role, anon included) on three tables that also happen to
--       carry the ordinary anon_all from step 1a. These three tables are
--       also in step 1a's array, so their "anon_all" is already gone and
--       each already has "authenticated_all" from
--       20260820_add_authenticated_rls_policies.sql -- nothing to add here,
--       just the extra PUBLIC policies to remove. ──
DROP POLICY IF EXISTS "anon select price_review_flags" ON public.price_review_flags;
DROP POLICY IF EXISTS "anon insert price_review_flags" ON public.price_review_flags;
DROP POLICY IF EXISTS "anon update price_review_flags" ON public.price_review_flags;

DROP POLICY IF EXISTS "anon select ndc_product_map" ON public.ndc_product_map;
DROP POLICY IF EXISTS "anon insert ndc_product_map" ON public.ndc_product_map;
DROP POLICY IF EXISTS "anon update ndc_product_map" ON public.ndc_product_map;

DROP POLICY IF EXISTS "anon select received_invoices" ON public.received_invoices;
DROP POLICY IF EXISTS "anon insert received_invoices" ON public.received_invoices;
DROP POLICY IF EXISTS "anon update received_invoices" ON public.received_invoices;

-- ── 2. The "invoices" Storage bucket -- was created fully public, serving
--       files over a plain public URL with no auth check of any kind. ──
UPDATE storage.buckets SET public = false WHERE id = 'invoices';

DROP POLICY IF EXISTS "anon upload invoices" ON storage.objects;
DROP POLICY IF EXISTS "anon read invoices"   ON storage.objects;
DROP POLICY IF EXISTS "anon update invoices" ON storage.objects;

DROP POLICY IF EXISTS "authenticated upload invoices" ON storage.objects;
DROP POLICY IF EXISTS "authenticated read invoices"   ON storage.objects;
DROP POLICY IF EXISTS "authenticated update invoices" ON storage.objects;

CREATE POLICY "authenticated upload invoices" ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'invoices');
CREATE POLICY "authenticated read invoices" ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id = 'invoices');
CREATE POLICY "authenticated update invoices" ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'invoices');

-- ── 3. security_invoker on every dashboard-supporting view -- without
--       this, a view can keep bypassing RLS on its own underlying table
--       even after steps 1-2, since Postgres views run as their owner's
--       privileges by default rather than the querying role's. ──
DO $$
DECLARE
  v text;
  views text[] := ARRAY[
    'v_avg_transaction_charge_daily', 'v_act_per_provider_daily',
    'v_case_heatmap', 'v_case_geo', 'v_case_volume_monthly',
    'v_clinical_kpis_daily', 'v_competitor_use_signal',
    'v_financial_kpis_daily', 'v_revenue_per_provider',
    'v_location_zip_counts', 'v_location_demographic_profile',
    'v_referral_case_volume'
  ];
BEGIN
  FOREACH v IN ARRAY views LOOP
    IF EXISTS (
      SELECT 1 FROM information_schema.views
      WHERE table_schema = 'public' AND table_name = v
    ) THEN
      EXECUTE format('ALTER VIEW public.%I SET (security_invoker = on)', v);
    END IF;
  END LOOP;
END $$;

COMMIT;
