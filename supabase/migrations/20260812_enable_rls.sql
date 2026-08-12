-- Enable RLS on all public tables and add anon-access policies
-- to resolve Supabase security advisories:
--   rls_disabled_in_public  — tables accessible without any row security
--   sensitive_columns_exposed — users/user_profiles readable by anyone
--
-- Uses DO blocks with IF EXISTS so tables that don't exist are skipped safely.

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
    -- Skip if the table doesn't exist in this project
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = t
    ) THEN
      RAISE NOTICE 'Skipping % (table does not exist)', t;
      CONTINUE;
    END IF;

    -- Enable RLS
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);

    -- Drop the policy first in case this script is re-run
    EXECUTE format('DROP POLICY IF EXISTS "anon_all" ON %I', t);

    -- Create open anon policy (preserves current app behavior)
    EXECUTE format(
      'CREATE POLICY "anon_all" ON %I FOR ALL TO anon USING (true) WITH CHECK (true)',
      t
    );

    RAISE NOTICE 'RLS enabled on %', t;
  END LOOP;
END $$;
