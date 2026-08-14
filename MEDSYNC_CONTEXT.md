# MedSync — Complete System Reference
*Use this document to brief Claude on what MedSync is and what every screen does.*

---

## What is MedSync?

MedSync is a veterinary practice inventory management SaaS built as a collection of standalone HTML files served from medsync.vet. It connects to a Supabase backend (project: aemkdummdrmxtwrkggjw) and integrates with Vetspire (practice management system) and Vetcove (veterinary purchasing platform). The app serves four Scout Care locations: Lincoln Park, Old Orchard, West Loop, and Wheaton.

The app runs inside a portfolio shell (`medsync_portfolio_live.html`) that loads all other screens as iframes. Child screens hide their own navigation when iframed and communicate with the shell via `postMessage`.

---

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS — no framework. All screens are single `.html` files.
- **Backend:** Supabase (PostgreSQL + REST API + Edge Functions + Auth + Storage)
- **Auth:** Supabase Auth; JWT stored in `localStorage.medsync_session`; user profile in `localStorage.medsync_user`
- **Edge Functions:** `send-welcome-email`, `writeback-queue`, `report-unknown-product`, `push-unit-cost`, `pill-count`, `trigger-intraday-sync`, `create-checkout`, `stripe-webhook`
- **External libs:** ZXing (barcode scanner), pdf.js (invoice parsing), XLSX (price audit), MedSyncExport (CSV/PDF export utility)
- **Integrations:** Vetspire GraphQL API, Vetcove CSV exports, Stripe (billing), FDA NDC API, Power BI (direct PostgreSQL connection)

## Roles (lowest → highest)
`receiver` → `clinical` → `inventory_lead` → `manager` → `hospital_manager` → `admin` → `medsync_superadmin`

## Location UUIDs
- Lincoln Park: `11111111-0000-0000-0000-000000000001` (Vetspire ID: 23083)
- Old Orchard: `11111111-0000-0000-0000-000000000002` (Vetspire ID: 27390)
- West Loop: `11111111-0000-0000-0000-000000000003` (Vetspire ID: 24356)
- Wheaton: `11111111-0000-0000-0000-000000000004` (Vetspire ID: 28253)

---

## Screens

---

### 1. Login (`medsync_login.html`)
**Access:** Public

- Email + password login via Supabase Auth
- Recent logins list (last 5, stored in localStorage)
- Forgot password → Supabase password recovery email
- Password reset mode: detects `#type=recovery` URL hash
- Blocks login if `users.is_active = false`
- On success: stores JWT + profile in localStorage, redirects to portfolio
- Welcome email login URL: `https://medsync.vet/medsync_login_v2.html`

**Reads:** `users` | **Writes:** None (Supabase Auth handles session)

---

### 2. Portfolio Shell (`medsync_portfolio_live.html`)
**Access:** All roles

The outer container for the entire app. Every other screen loads inside an iframe here.

- Sticky topbar: logo, role badge, avatar, hamburger
- Left sidebar: role-scoped links to all screens
- Iframe content area: loads child screens
- Portfolio dashboard: org-wide snapshot KPI cards, priority chips (expiring lots, pending POs, expired-not-disposed), live activity feed, location/region filter, recognition and compliance scores by location
- Propagates location context to child frames via `postMessage`
- Listens for `settings_synced` from Settings screen to update COGs% across all screens

**Reads:** `locations`, `lots`, `po_items`, `activity_log`, `cycle_counts`, `users`

---

### 3. Analytics & Reports (`medsync_analytics_live.html`)
**Access:** Admin, hospital_manager, inventory_lead

Primary financial and operational KPI dashboard.

- Date range: 11 options (Today → Custom)
- Region/location filter
- KPI row: COGs%, GPO savings, goods lost $, expiring lots
- COGs by location horizontal bar chart vs. target range
- 7 tabs: Overview, COGs Breakdown, Goods Lost, Lot Lifecycle, Supplier Breakdown, Top Items, Cycle Count Compliance
- COGs% target range from `organization_settings` (`cogs_min`/`cogs_max`, default 8–10%)
- Export: CSV, PDF, QuickBooks-formatted CSV
- Power BI: direct PostgreSQL connection info (`db.aemkdummdrmxtwrkggjw.supabase.co:5432`)

**Reads:** `goods_lost`, `po_items`, `lots`, `dispensed_items`, `daily_revenue`, `cycle_counts`, `purchase_history`, `location_settings`, `inventory_snapshots`, `locations`

---

### 4. Lot Lifecycle (`medsync_lot_lifecycle_live.html`)
**Access:** All roles

Tracks every product lot from receiving through expiration/disposal.

- Default view: all non-disposed lots, sorted by soonest expiry
- Status badges: Active (green), Expiring Soon ≤30 days (amber), Expired (red)
- Search by lot#, NDC, or product name
- Filters: region, location, product, status tab
- Lot detail modal: qty received/remaining, lot#, expiry, received date, vendor, notes
- **Mark Disposed button** — appears inline on every Expired row; one-click disposal with confirm dialog; removes lot from list immediately; logs event to `activity_log`
- "Log disposal" also available inside the detail modal
- Vaccine return workflow: generates return documentation
- ZXing barcode scanner for lot number lookup
- Export: CSV and PDF
- Disposed lots are excluded from the fetch query (`status=neq.Disposed`)

**Reads:** `lots` (joined with `products`, `locations`, `users`) | **Writes:** `lots` (PATCH status, qty_remaining)

---

### 5. Purchase Orders / Weekly Order (`medsync_weekly_order_live.html`)
**Access:** All roles

Weekly reorder workflow based on Vetspire inventory levels.

- PO window banner: Monday–Tuesday 1:00 PM CT (Vetcove cutoff)
- Auto-flags products where Vetspire on_hand < qty_min
- Location and week selectors
- Product table: name, vendor, qty min/max, on-hand (from Vetspire snapshot), suggested order qty, unit price, GPO price, status
- Vetspire snapshot matching: Jaccard fuzzy match (threshold 0.25)
- Add item manually via product picker
- Submit order: writes `po_items` with `status='submitted'`
- Budget summary: weekly spend vs. COGs target (falls back to `organization_settings.cogs_min` if no location setting)
- Export: CSV and PDF

**Reads:** `po_items`, `products`, `product_locations`, `inventory_snapshots`, `lots`, `daily_revenue`, `location_settings`, `purchase_history`, `locations`
**Writes:** `po_items` (INSERT), `purchase_history`

---

### 6. COGS Import (`medsync_cogs_import_live.html`)
**Access:** Admin, hospital_manager

Imports Vetcove Order History Items CSV to log drug spend into MedSync purchase history. Used to populate the Budget vs Spend table with historical COGS data.

- **CSV format:** Vetcove Order History Items (itemized — one row per line item, 21 columns)
- Key columns used: `Vetcove Item ID` (col 11, dedup key), `Total Price` (col 18, spend amount), `Item Status` (col 19, skip non-Completed)
- **Step 1:** Upload CSV + select location + set COGs Budget Target % (defaults from `organization_settings.cogs_min`)
- **Step 2:** Preview — week-by-week Budget vs Spend table covering the full CSV date range
  - Revenue pulled from `daily_revenue` (via Vetspire location ID bridge)
  - Weeks with no revenue data show estimated revenue (avg of known weeks) with "Est" badge
  - Over-budget weeks highlighted in red; title shows location + full date range
  - Each week label includes year: e.g., "Mar 23 – Mar 29, 2026"
  - Dedup: checks existing `purchase_history` for `VID:{vetcoveItemId}` in note field; skips already-imported rows
  - 5 summary tiles: YTD Budget, YTD Spend, YTD Variance, Actual COGs%, Excluded rows
- **Step 3:** Import — writes each line item to `purchase_history`
  - `source = 'vetcove_import'`
  - `note` format: `VID:{vetcoveItemId} · {itemName} · Order {#} · {supplier} · RATE:{cogsTargetPct}`
  - `RATE:` in note locks in the COGs budget % at time of import for historical accuracy
- COGs target % input: changing this in Settings updates this screen's default
- Portfolio and Analytics both already include `source=vetcove_import` in their spend queries

**Reads:** `locations`, `organization_settings`, `purchase_history`, `daily_revenue`
**Writes:** `purchase_history` (INSERT, `source='vetcove_import'`)

---

### 7. Settings (`medsync_settings_live.html`)
**Access:** Admin

Organization-wide configuration panel.

- **COGs thresholds:** `cogs_min` (default 8%), `cogs_max` (default 10%) — propagated to Analytics, COGS Import default, and Weekly Order fallback
- Goods lost threshold: `gl_pct_thresh` (triggers banner in Goods Lost screen)
- Expiry alert days: `exp_days` (days ahead to flag "Expiring Soon")
- Unreceived days: `unreceived_days` (days before submitted PO marked overdue)
- Min stock enabled toggle, white goods % range, PO cutoff time
- Margin targets (superadmin-only, visible to @scoutcare.com / @medsync.vet)
- Vetcove API key, Vetspire API key (saved to localStorage)
- Power BI connection details (localStorage)
- Email insights toggle per user
- **Billing section:** current tier, billing change log; plan changes require 6-digit OTP via email; 14-day lock between changes; writes to `billing_change_log`
- Settings saved to both `localStorage` and `organization_settings`; broadcasts `settings_synced` to parent frame

**Reads:** `organization_settings`, `users`, `organizations`, `billing_change_log`
**Writes:** `organization_settings` (upsert), `users` (PATCH email_insights_enabled), `billing_change_log`

---

### 8. Users (`medsync_users_live.html`)
**Access:** Admin (full), hospital_manager (manager/staff only), inventory_lead (receiver only)

User management across the organization.

- User table: name, email, role badge, location(s), last active, status
- Search by name or email; filter by role, location, active/inactive
- **New User:** full name, email, role (scoped by your role), location(s), access scope; creates Supabase Auth account with temp password `MedSync2026!`; sends welcome email via `send-welcome-email` Edge Function
- Edit: change role, reassign locations, toggle active
- Password reset: Supabase Auth password reset email
- Deactivate: sets `is_active=false`; historical data preserved

**Reads:** `users`, `regions`, `locations` | **Writes:** `users` (INSERT/PATCH/soft delete)
**Integrations:** Supabase Auth, Edge Function `send-welcome-email`

---

### 9. Activity Log (`medsync_activity_log_live.html`)
**Access:** All roles (managers/staff see their location only)

Immutable audit trail of all MedSync actions.

- Event types: order, receive, goods, lot, user, count
- Filters: free text, region, location, date range, event type, role
- Table: timestamp, event type badge, user + role, location, description
- Detail modal: full metadata JSON, session ID, IP, reference ID
- CSV export (filtered)
- Limit: 200 most recent events per query

**Reads:** `activity_log` (joined with `users`, `locations`) | **Writes:** None

---

### 10. Profile (`medsync_profile_live.html`)
**Access:** All roles (own profile only)

- Edit display name, email
- Password change via Supabase Auth
- Avatar: 8 built-in SVG animal avatars OR custom photo upload (resized to 400px JPEG, stored in Supabase Storage)
- Bio (200 char limit)

**Reads:** `user_profiles` | **Writes:** `user_profiles` (upsert), `users` (PATCH name/email)

---

### 11. Cycle Count (`medsync_cycle_count_live.html`)
**Access:** All roles

Physical inventory cycle count by ABC/D category rotation.

- **Category schedule:**
  - Cat A: controlled substances, vaccines, emergency drugs — weekly
  - Cat B: injectables, IV fluids, biologics — biweekly (weeks 1+3)
  - Cat C: oral meds — biweekly (weeks 2+4)
  - Cat D: white goods (gauze, syringes, supplies) — monthly (week 4 only)
- Due banner shows which categories are due this week
- Product table per tab: expected on-hand (from Vetspire snapshot), actual count input, variance %, status
- Variance thresholds: >25% = Discrepancy (red), 10–25% = Warning (amber), ≤10% = Match (green)
- Lot entry required per product before submit
- Submit modal: review all discrepancies before confirming
- Vetspire writeback for Wheaton via `writeback-queue` Edge Function
- ZXing barcode scanner, CSV/PDF export

**Reads:** `inventory_snapshots` | **Writes:** `activity_log`, `lots`
**Integrations:** Vetspire writeback (Wheaton only)

---

### 12. Goods Lost (`medsync_goods_lost_live.html`)
**Access:** All roles

Log pharmaceutical or goods losses.

- Loss categories: Diagnostic duplicate (4 sub-types), Expired product, Damaged/Spilled, Medication waste, In-house use, DEA Controlled Waste (requires DEA log note), Other
- Routing insight panel for diagnostic duplicates
- GL% threshold banner when MTD GL exceeds `gl_pct_thresh` from organization settings
- History panel: 5 most recent submissions + MTD total
- Vendor return: "Print" button generates printable return document (Zoetis: 1-888-963-8471; Boehringer Ingelheim: 1-800-325-9167)

**Reads:** `locations`, `products`, `goods_lost`, `po_items` | **Writes:** `goods_lost`, `activity_log`

---

### 13. Receiving (`medsync_receiving_live.html`)
**Access:** All roles

Full receiving workflow — adds inbound stock to inventory.

- PO group cards by vendor + week
- Overdue alert for POs older than `unreceived_days`
- ZXing barcode scanner + manual entry
- **Lot entry modal:** lot#, expiration MM/YYYY, qty received (required per item)
- **Pill count:** camera capture → `pill-count` Edge Function (AI count + confidence)
- **Price drift alert:** flags when invoice price differs >2% from unit cost; writes to `price_review_flags`
- **NDC resolve:** unknown barcode → checks `ndc_product_map` → FDA NDC API → `report-unknown-product` Edge Function
- Loss options per item: Expired, Damaged, Vendor return, Medication waste
- On complete: creates `receiving_sessions`, upserts `lots`, writes to `vetspire_writeback_queue`, PATCHes `po_items` to received, logs to `activity_log`
- Invoice PDF upload after completion → Supabase Storage → `received_invoices`

**Reads:** `locations`, `po_items`, `products`, `ndc_product_map`
**Writes:** `po_items`, `lots`, `goods_lost`, `activity_log`, `ndc_product_map`, `price_review_flags`, `receiving_sessions`, `received_invoices`, `vetspire_writeback_queue`
**Integrations:** ZXing, FDA NDC API, Edge Functions: `pill-count`, `report-unknown-product`, `push-unit-cost`

---

### 14. Hospital Receiver (`medsync_hospital_receiver_live.html`)
**Access:** No login required

Simplified touch-friendly receiving for non-authenticated hospital staff. URL-accessible without credentials.

- 5-screen state machine: welcome → task → receive → goods → done
- Lists submitted PO groups for the selected location
- Inline loss reporting per item
- Auto-generated lot/expiry simulation values (not real scanning)

**Reads:** `locations`, `po_items` | **Writes:** `po_items`, `lots`, `goods_lost`, `activity_log`

---

### 15. Invoice Reconciliation (`medsync_invoice_reconcile_live.html`)
**Access:** Admin/Manager

Upload vendor invoice PDFs and reconcile against open POs.

- Sidebar (invoice list with status badges) + detail panel
- PDF upload zone; vendor auto-detected from PDF text
- Supported vendors: MWI, Midwest Veterinary, Covetrus, Patterson, Medline, Amatheon, Wedgewood, Vetcove, Zoetis, Dechra, Merck; generic fallback
- Jaccard matching (threshold 0.30) to align invoice lines to PO items
- Price variance and qty variance computed per line
- Line statuses: matched, price_discrepancy, qty_mismatch, not_on_po, approved, unmatched
- Approve per line or approve whole invoice
- Un-invoiced POs banner (POs submitted >5 days with no invoice)

**Reads:** `invoices`, `invoice_items`, `po_items`
**Writes:** `invoices` (INSERT/PATCH), `invoice_items` (INSERT/PATCH), DELETE invoices

---

### 16. Received Invoices (`medsync_received_invoices_live.html`)
**Access:** All authenticated

View and manage invoice documents attached to completed receiving sessions.

- Search by vendor, invoice#, PO reference; filter by location + date range
- Detail panel: PDF preview (pdf.js), items received table, upload zone for missing invoices, notes
- Upload: Supabase Storage bucket `invoices` → PATCH `received_invoices`

**Reads:** `received_invoices`, `receiving_sessions`, `po_items`
**Writes:** `received_invoices` (PATCH invoice_url, notes)

---

### 17. Price Audit (`medsync_price_audit_live.html`)
**Access:** Admin/superadmin

Three-tab price comparison, audit queue, and VetSpire price sync tool.

**Tab 1 — Price Comparison:**
- Upload Vetcove CSV, Excel, or vendor PDF invoice
- Optional VetSpire products CSV to load purchase costs
- Matches by NDC (exact) then name (Jaccard 0.55 threshold)
- Package normalization (volumetric unit conversion, pkg÷N ratio)
- Stats: matched, Vetcove higher/lower, >20% drift, flagged
- Filter by drift level and match type
- "Flag for Audit" per row → `price_review_flags`
- "Push to VetSpire" per row → `push-unit-cost` Edge Function
- Batch select: save costs or save SKUs for multiple rows
- "Intraday sync" trigger after SKU saves

**Tab 2 — Audit Queue:**
- Loads `price_review_flags`, status tabs: Pending / Approved / Rejected / All
- Per-row: Approve (with new cost → pushes to VetSpire), Hold, Reject
- Bulk approve/reject

**Tab 3 — VetSpire Prices:**
- Upload VetSpire mass products CSV
- Compares unit costs; sync drifted items via `push-unit-cost`
- ZXing camera scanner for UPC capture

**Reads:** `active_products` view, `price_review_flags`, `locations`
**Writes:** `price_review_flags`, `products` (PATCH sku via push-unit-cost)
**Integrations:** Edge Functions: `push-unit-cost`, `trigger-intraday-sync`; Vetspire

---

### 18. Quarterly Report (`medsync_quarterly_report_live.html`)
**Access:** All roles

Quarterly financial summary for ownership/board review.

- Year selector + location selector
- KPI row: Total Spend, Est. GPO Savings (12% of spend), Goods Lost $, Active Lots, Expiring/Expired Lots
- Quarterly breakdown table: Q1–Q4 + Full Year (spend, GPO savings, goods lost, GL%, units ordered)
- Spend vs. Goods Lost trend bar chart
- Top 10 Products by Spend table
- Goods Lost by Category breakdown
- Export: CSV and PDF

**Reads:** `po_items`, `goods_lost`, `lots` | **Writes:** None

---

### 19. Reports (`medsync_reports_live.html`)
**Access:** All roles

Annual management reports across 5 sections.

- **Counts on Hand:** active lots, units on hand, expiring/expired counts; product table (100 rows max)
- **Spending:** monthly bar chart, quarterly table, top vendors; uses `purchase_history` if available, falls back to `po_items`
- **Goods Lost:** monthly chart, quarterly table, by-category breakdown
- **Order History:** last 200 orders with full detail
- **Integrity Assessment:** automated risk signal engine:
  - High vague GL category ratio (>25% Other/Unknown)
  - Controlled substance losses recorded
  - Goods lost >8% of spend (High) or >4% (Medium)
  - Expired lots with remaining qty (possible under-reporting)
  - Locations with orders but zero GL (possible under-reporting)
  - Vendor returns/credits tracked (informational)
  - Outputs: score (Low Risk / Needs Review / High Risk) + flag cards

**Reads:** `po_items`, `goods_lost`, `lots`, `purchase_history` | **Writes:** None

---

### 20. Regions (`medsync_regions_live.html`)
**Access:** Admin

Manage organizational regions and assign locations to them.

- Region cards: name, description, location count, location list
- Create, rename, delete regions
- Move locations between regions
- Delete blocked if locations still assigned

**Reads:** `regions`, `locations` | **Writes:** `regions`, `locations` (PATCH region_id)

---

### 21. New Location (`medsync_newlocation_live.html`)
**Access:** Admin

Multi-step wizard for onboarding a new practice location.

- Type: De Novo (new build with opening order) or Existing Practice (PIMS import)
- Practice types: Urgent Care, General Practice, Emergency (ER), Specialty
- Address form with GPS geolocation + autocomplete; region assignment
- **De Novo:** generates full minimum opening order (200+ items across 11 categories); editable qty; CSV + PDF export; saves location to Supabase on PDF export
- **Existing Practice:** Vetspire PIMS import (live); EzyVet/Cornerstone/AVImark (coming soon)
- Plan/tier display: slots used vs. remaining; upgrade prompt
- Stripe integration: tier upgrades → Stripe checkout (test mode)

**Reads:** `organizations`, `locations`, `regions`
**Writes:** `locations` (INSERT), `regions` (INSERT if new)
**Integrations:** Stripe, GPS/geolocation

---

### 22. Vetcove Import (`medsync_vetcove_import_live.html`)
**Access:** All roles

Import Vetcove return credits into Goods Lost. (Different from COGS Import — this is specifically for vendor return credits.)

- Prior import detection: auto-skips rows from already-imported dates
- Product matching: exact → contains → first-word fallback
- Category mapping from CSV reason field
- Writes to `goods_lost` with note: `'Imported from Vetcove export · {date} · Order {#}'`

**Reads:** `products`, `locations`, `goods_lost` | **Writes:** `goods_lost`

---

### 23. User Guide (`medsync_userguide_live.html`)
**Access:** All roles

Interactive onboarding training guide.

- Role-gated sections: Staff Guide, Admin Guide, MedSync Internal
- Countdown banner within 30 days of account creation
- Sticky TOC sidebar
- **Quiz:** 5 questions per section, pass = 4/5; certificate modal on pass (stored in localStorage)
- **Sandbox mode:** full-screen iframe of live screens with collapsible guide panel alongside
- Staff Guide: Cycle Count, Receiving, Weekly Order, Goods Lost SOPs
- Admin Guide: all 12+ admin screen overviews
- MedSync Internal: provisioning, support escalation, billing/Stripe reference

**Reads/Writes:** None (quiz results and certification stored in localStorage only)

---

### 24. Platform Admin (`medsync_platform_admin.html`)
**Access:** `medsync_superadmin` only (MedSync internal staff)

Internal tool for managing all customer organizations.

- **Organizations tab:** org table, org detail panel, "Provision new customer" 4-step wizard (create auth account → user profile → org record → send welcome email)
- **Billing tab:** MRR/ARR summary, pending changes, subscription table, manual tier correction with OTP
- **Super Admins tab:** list + add super admin
- **Growth tab:** business metrics, pricing tiers (Solo $149, Small Group $249, Mid Group $349, Large Group $449, Enterprise custom), roadmap through 2030
- **Onboarding tab:** 4-column kanban pipeline, staff guide, sandbox management

**Reads:** `organizations`, `locations`, `users`, `billing_change_log`
**Writes:** `organizations`, `users`, `billing_change_log`
**Integrations:** Supabase Auth, `send-welcome-email` Edge Function, Stripe

---

### 25. Unsubscribe (`medsync_unsubscribe.html`)
**Access:** Public (email link)

- URL params: `uid` + `action` (unsubscribe or resubscribe)
- PATCHes `users.email_insights_enabled` on page load

**Writes:** `users` (PATCH email_insights_enabled)

---

### 26. Wheaton Lot Sync (GitHub Actions workflow)
**File:** `wheaton_lot_sync.py` + `.github/workflows/lot_sync.yml`

- Scheduled daily GitHub Actions workflow
- Fetches all inventory adjustments for Wheaton from Vetspire GraphQL API
- Aggregates by (product, lot_number) to compute net quantity per lot
- Upserts results into Supabase `lots` table for Wheaton (replaces all rows where `notes LIKE 'Vetspire inventory:%'`)
- Reads `~/.vetspire_token` (stored as GitHub Actions secret)

---

## Key Database Tables

| Table | Purpose |
|---|---|
| `users` | User accounts (full_name, email, role, is_active, location_id, organization_id) |
| `user_profiles` | Extended profile (avatar_b64, bio, first_name, last_name) |
| `organizations` | Customer organizations (tier, location_limit, status) |
| `organization_settings` | Org-wide settings JSON (cogs_min, cogs_max, gl_pct_thresh, etc.) |
| `locations` | Practice locations (name, region_id, practice_type) |
| `location_settings` | Per-location settings (cogs_pct — legacy) |
| `regions` | Location groupings |
| `products` | Product catalog (name, ndc, sku, upc, unit_cost, vendor, is_controlled, dea_schedule) |
| `product_locations` | Which products are active at which locations |
| `lots` | Inventory lots (lot_number, expiration_date, qty_received, qty_remaining, status, location_id) |
| `po_items` | Purchase order line items (status: submitted/received) |
| `purchase_history` | All logged drug spend (source: vetcove/vetcove_weekly/vetcove_import) |
| `daily_revenue` | Daily gross production revenue from Vetspire by location |
| `goods_lost` | Loss events (category, qty, value, notes) |
| `inventory_snapshots` | Vetspire on-hand counts synced daily |
| `dispensed_items` | Items dispensed in Vetspire |
| `activity_log` | Immutable audit trail of all app actions |
| `price_review_flags` | Flagged price discrepancies (status: pending/approved/rejected) |
| `ndc_product_map` | NDC→product cache for barcode scanning |
| `receiving_sessions` | Completed receiving session records |
| `received_invoices` | Invoice documents attached to receiving sessions |
| `invoices` / `invoice_items` | Invoice reconciliation records |
| `messages` / `message_reads` | In-app messaging |
| `billing_change_log` | Audit trail for tier/billing changes |
| `vetspire_writeback_queue` | Queue for pushing cycle count results back to Vetspire |
| `active_products` | View: active products with joined cost/NDC data |

---

## Important Business Rules

1. **COGs target %** is set org-wide in Settings (`organization_settings.cogs_min`/`cogs_max`). This value flows to Analytics, COGS Import default input, and Weekly Order fallback. `location_settings.cogs_pct` is a legacy separate system.
2. **COGS Import dedup key** is `VID:{vetcoveItemId}` stored in the `note` field of `purchase_history`. Each record also stores `RATE:{pct}` to lock in the COGs target at time of import.
3. **Disposed lots** are excluded from the Lot Lifecycle fetch query (`status=neq.Disposed`). Once marked disposed, they don't appear in the list.
4. **Vetspire writeback** only applies to Wheaton (`location_id = 11111111-0000-0000-0000-000000000004`, Vetspire ID 28253).
5. **All spend sources** included in Analytics/Portfolio COGs: `source=in.(vetcove,vetcove_weekly,vetcove_import)`.
6. **API keys** (Resend, Vetspire) live in Supabase secrets only. Email goes through `send-email` Edge Function — never a direct API key in HTML.
7. **Billing changes** require a 6-digit OTP sent to the admin's email and have a 14-day lock period between changes.
8. **RLS** is enabled on all Supabase tables with explicit `anon` policies (added August 2026).
