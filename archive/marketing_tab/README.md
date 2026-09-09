# Marketing tab — archived, not active

The Marketing tab (Case Volume by Referring Vet, Revenue by Referring
Hospital, Referral Origin Map, Weekly Marketing Insights) was removed from
ScoutSync on request. Everything needed to bring it back is kept here
instead of only living in git history, so it doesn't need an archaeology
session to find later.

## What's in this folder

Full snapshots of the three files as they stood immediately before removal
(commit `9f2e6d4`, one commit before the removal commit
`43ac455`) — not diffs, so there's no risk of a stale patch failing to
apply after later unrelated edits to these files:

- `scoutsync_dashboard_with_marketing.html` — the complete dashboard with
  the Marketing tab intact. The tab-specific pieces, if you want to
  extract just those instead of diffing the whole file:
  - Nav button: `<button data-tab="marketing">Marketing</button>`
  - CSS: the `--c-marketing` color var, and the `#referral-map` half of
    the (now split) `#chicago-map, #referral-map` rule
  - HTML: the `<section class="panel" id="panel-marketing">` block
  - JS: `initReferralMap`, `renderReferralMap`, `renderMarketingInsights`,
    `loadMarketing`, and the two `activeTab === 'marketing'` dispatch
    lines (in the tab-router and the map-resize-on-tab-switch handler)
- `vetspire_clinical_sync_with_marketing.py` — has the `rdvm { ... city
  state postalCode }` fields on the `clientRdvms` query, and the
  `referrals` dict populating `vetspire_rdvm_id`/`city`/`state`/
  `postal_code`, that the current (reverted) version dropped
- `vetspire_financial_sync_with_marketing.py` — has the
  `SYNC_RDVM_REVENUE`-gated `RDVM_ID` salesReport breakdown and
  `rdvm_revenue_daily` upsert that the current version dropped
- `vetspire_rdvm_directory_sync.py` — the standalone full-directory sync
  script, deleted from the repo root
- `workflows/vetspire_rdvm_directory_sync.yml`,
  `workflows/vetspire_rdvm_revenue_sync.yml` — the two dedicated GitHub
  Actions workflows, deleted from `.github/workflows/`. Kept here under a
  different path on purpose — GitHub Actions only picks up workflow files
  that live under `.github/workflows/`, so they're inert here and won't
  start running just by existing in the repo.

## What's NOT archived here (because it was never deleted)

The two original migrations are still sitting in `supabase/migrations/`,
untouched:
- `scoutsync_referral_marketing_analytics.sql`
- `scoutsync_rdvm_directory.sql`

Repo convention is to never delete a migration file once written, so
these were left in place even though the removal migration
(`scoutsync_remove_marketing_tab.sql`) drops the database objects they
create. If you restore Marketing, re-run both of them in order (they're
idempotent — `create table/view if not exists`/`create or replace view`) to
rebuild `rdvm_directory`, `rdvm_revenue_daily`, `v_referral_case_volume`,
and the 4 columns on `referral_relationships`.

## To restore

1. Re-run `scoutsync_referral_marketing_analytics.sql` then
   `scoutsync_rdvm_directory.sql` in the Supabase SQL editor.
2. Copy the relevant pieces (or the whole files) from this folder back
   into `scoutsync_dashboard.html`, `vetspire_clinical_sync.py`, and
   `vetspire_financial_sync.py`.
3. Restore `vetspire_rdvm_directory_sync.py` to the repo root, and both
   workflow files to `.github/workflows/`.
4. Dispatch `vetspire_rdvm_directory_sync.yml` once manually to repopulate
   `rdvm_directory` (it's a full listing, not incremental — safe to
   re-run any time), and `vetspire_rdvm_revenue_sync.yml` to backfill
   `rdvm_revenue_daily`.

**Note**: if `scoutsync_remove_marketing_tab.sql` has already been run,
`rdvm_directory`'s prior synced rows and `rdvm_revenue_daily`'s revenue
history are gone for good — restoring the code brings the feature back,
but the two syncs above will need to run fresh to repopulate the data
from Vetspire again.
