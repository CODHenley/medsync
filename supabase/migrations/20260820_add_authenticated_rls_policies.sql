-- 20260812_enable_rls.sql enabled RLS on every table below but only added an
-- "anon" policy. Real logged-in users authenticate via Supabase Auth
-- (medsync_login.html's /auth/v1/token?grant_type=password) and their stored
-- access_token is a genuine per-user JWT — Postgres role `authenticated`, not
-- `anon`. With no authenticated-role policy, every request sent with that
-- real token was silently denied by RLS (SELECT returns 0 rows, INSERT/UPDATE
-- rejected) rather than erroring, which is invisible unless you notice the
-- numbers/behavior don't add up.
--
-- Confirmed root cause of the onboarding "set up a new password" screen
-- appearing on every login: obCheck() reads user_profiles.onboarding_complete
-- using the user's real token, always gets 0 rows back (RLS, not a missing
-- row), so the wizard always re-shows; "Skip" doesn't stick either, because
-- the write that's supposed to persist it is denied the same way.
--
-- anon_all already grants unrestricted access to anyone holding the anon key
-- (which ships in the client-side JS, so it's effectively public already).
-- Adding an equivalent authenticated_all policy does not lower security below
-- that existing baseline — it only restores the access logged-in users were
-- always supposed to have.

DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'daily_revenue',
    'purchase_history',
    'locations',
    'products',
    'lots',
    'po_items',
    'goods_lost',
    'dispensed_items',
    'cycle_counts',
    'inventory_snapshots',
    'activity_log',
    'price_review_flags',
    'ndc_product_map',
    'receiving_sessions',
    'invoices',
    'invoice_items',
    'received_invoices',
    'order_lines',
    'purchase_orders',
    'active_products',
    'physical_count_sessions',
    'physical_count_items',
    'vetspire_writeback_queue',
    'quiz_completions',
    'messages',
    'message_reads',
    'regions',
    'location_settings',
    'organization_settings',
    'billing_change_log',
    'users',
    'user_profiles',
    'organizations'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = t AND table_type = 'BASE TABLE'
    ) THEN
      RAISE NOTICE 'Skipping % (does not exist or is a view)', t;
      CONTINUE;
    END IF;

    EXECUTE format('DROP POLICY IF EXISTS "authenticated_all" ON %I', t);
    EXECUTE format(
      'CREATE POLICY "authenticated_all" ON %I FOR ALL TO authenticated USING (true) WITH CHECK (true)',
      t
    );

    RAISE NOTICE 'authenticated policy added on %', t;
  END LOOP;
END $$;
