-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Remove the Marketing tab and all its backend objects
-- Run in: Supabase Dashboard → SQL Editor
--
-- The Marketing tab (Case Volume by Referring Vet, Revenue by Referring
-- Hospital, Referral Origin Map, Weekly Marketing Insights) has been
-- removed from the dashboard, along with the Vetspire syncs that fed it
-- (vetspire_rdvm_directory_sync.py, the RDVM_ID salesReport breakdown in
-- vetspire_financial_sync.py, and the extra rdvm fields
-- vetspire_clinical_sync.py pulled into referral_relationships). This
-- migration drops the database objects that were built ONLY for that
-- tab -- it does NOT touch referral_relationships itself or its original
-- columns (vetspire_referral_id/client_id/referral_name/referral_type/
-- listed_at), which predate Marketing and still back the Clinical
-- Operations competitor-use signal (v_competitor_use_signal,
-- scoutsync_clinical_financial_schema.sql).
--
-- Order matters: v_referral_case_volume selects
-- referral_relationships.vetspire_rdvm_id, so the view must be dropped
-- BEFORE that column, or Postgres refuses the alter ("2BP01: cannot drop
-- column ... because other objects depend on it" -- the same error class
-- scoutsync_invoice_total.sql called out when it dropped
-- estimated_case_value).
--
-- This is destructive and NOT reversible -- rdvm_directory (1,150+ synced
-- rows) and rdvm_revenue_daily's revenue history are permanently deleted
-- once this runs. Only run it once you're sure Marketing is staying gone.
-- ══════════════════════════════════════════════════════════════

drop view if exists public.v_referral_case_volume;

alter table public.referral_relationships
  drop column if exists vetspire_rdvm_id,
  drop column if exists city,
  drop column if exists state,
  drop column if exists postal_code;

drop table if exists public.rdvm_revenue_daily;
drop table if exists public.rdvm_directory;
