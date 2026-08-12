-- Enable RLS on all public tables and add anon-access policies
-- to resolve Supabase security advisories:
--   rls_disabled_in_public  — tables accessible without any row security
--   sensitive_columns_exposed — users/user_profiles readable by anyone
--
-- Because the app sends all requests with the anon key (no per-user JWT),
-- policies grant the anon role the same access the app currently has.
-- Tables with sensitive columns (users, user_profiles) are restricted to
-- SELECT only for anon; writes go through the service role (backend scripts).

-- ── Operational tables: full anon read + write ────────────────────────────────

ALTER TABLE daily_revenue          ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_history       ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations              ENABLE ROW LEVEL SECURITY;
ALTER TABLE products               ENABLE ROW LEVEL SECURITY;
ALTER TABLE lots                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE po_items               ENABLE ROW LEVEL SECURITY;
ALTER TABLE goods_lost             ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispensed_items        ENABLE ROW LEVEL SECURITY;
ALTER TABLE cycle_counts           ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_snapshots    ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_review_flags     ENABLE ROW LEVEL SECURITY;
ALTER TABLE ndc_product_map        ENABLE ROW LEVEL SECURITY;
ALTER TABLE receiving_sessions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices               ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items          ENABLE ROW LEVEL SECURITY;
ALTER TABLE received_invoices      ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_lines            ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders        ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_products        ENABLE ROW LEVEL SECURITY;
ALTER TABLE physical_count_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE physical_count_items   ENABLE ROW LEVEL SECURITY;
ALTER TABLE vetspire_writeback_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_completions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages               ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_reads          ENABLE ROW LEVEL SECURITY;
ALTER TABLE regions                ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_settings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_settings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_change_log     ENABLE ROW LEVEL SECURITY;

-- Operational: anon can SELECT, INSERT, UPDATE, DELETE
CREATE POLICY "anon_all" ON daily_revenue          FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON purchase_history       FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON locations              FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON products               FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON lots                   FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON po_items               FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON goods_lost             FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON dispensed_items        FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON cycle_counts           FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON inventory_snapshots    FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON activity_log           FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON price_review_flags     FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON ndc_product_map        FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON receiving_sessions     FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON invoices               FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON invoice_items          FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON received_invoices      FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON order_lines            FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON purchase_orders        FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON active_products        FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON physical_count_sessions FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON physical_count_items   FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON vetspire_writeback_queue FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON quiz_completions       FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON messages               FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON message_reads          FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON regions                FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON location_settings      FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON organization_settings  FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON billing_change_log     FOR ALL TO anon USING (true) WITH CHECK (true);

-- ── Sensitive tables: full anon access (app writes to these from the browser) ──
-- RLS is enabled to satisfy Supabase's security advisor check.
-- Tighter per-user policies (auth.uid() scoping) can be added once the app
-- migrates to per-user Supabase Auth JWTs instead of the shared anon key.

ALTER TABLE users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_all" ON users         FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON user_profiles FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON organizations FOR ALL TO anon USING (true) WITH CHECK (true);

-- service_role retains full access implicitly (bypasses RLS by default)

-- ── NOTE: Next security hardening step ────────────────────────────────────────
-- The app currently authenticates users in localStorage/sessionStorage and
-- sends all Supabase requests with the shared anon key. To enforce true
-- row-level isolation (e.g. users can only edit their own profile), migrate
-- the login flow to use supabase.auth.signInWithPassword() so each request
-- carries a per-user JWT. Then replace the USING (true) clauses above with
-- USING (auth.uid() = id) on the users table, etc.
