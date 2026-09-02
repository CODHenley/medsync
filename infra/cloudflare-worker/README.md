# ScoutSync standalone domain

Setup notes for giving ScoutSync its own domain (separate from MedSync's
`medsync.vet`) while keeping one codebase and one Supabase backend.

## What this is

`scoutsync-proxy.js` is a Cloudflare Worker script. It's the only piece of
this setup that lives outside this repo's normal deploy — Cloudflare
doesn't read from GitHub, so the script has to be pasted into the
Cloudflare dashboard directly. It's kept here so the setup has a real,
version-controlled source of truth instead of living only in Cloudflare's
UI.

## What you need to do

1. **Register the new domain** with whatever registrar you used for
   `medsync.vet`.
2. **Create a free Cloudflare account** (if you don't already have one)
   and add the new domain to it. Cloudflare will give you two nameservers
   to set at your registrar — do that, then wait for Cloudflare to show
   the domain as active (usually minutes to a few hours).
3. **Create the Worker**: Cloudflare dashboard → Workers & Pages → Create
   → paste in `scoutsync-proxy.js`'s contents → deploy.
4. **Attach the domain to the Worker**: on that Worker → Settings →
   Triggers → Custom Domains → add the new domain (and `www.` if you want
   it too). Cloudflare provisions TLS automatically — no certificate work
   needed.
5. **Verify**: visiting the new domain should load the live ScoutSync
   dashboard, identical to `medsync.vet/scoutsync_dashboard.html` today.

## Why this approach

- **No repo split, no data migration.** The dashboard keeps deploying via
  the existing `deploy_pages.yml` workflow to `medsync.vet`, and its own
  JavaScript keeps talking to the same Supabase project directly from the
  browser — this Worker only proxies the initial HTML/asset request.
- **GitHub Pages only supports one custom domain per repo**, which is why
  a second domain can't just be added directly in this repo's Pages
  settings — the Worker is what makes a second domain possible without
  duplicating the codebase into a second repo.
- Cost: Cloudflare's free tier covers this (a Worker proxying one static
  page is nowhere near the free tier's request limits).

## If ScoutSync ever needs its own Supabase project

Not part of this setup — kept shared per the current decision. If that
changes later, that's a real data-migration project (schema, RLS
policies, and every `vetspire_*_sync.py` script's target project), not a
DNS change.
