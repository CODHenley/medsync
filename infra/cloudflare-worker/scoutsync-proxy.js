// ScoutSync domain proxy — Cloudflare Worker
//
// Lets a new, standalone ScoutSync domain (e.g. scoutsync.vet) serve the
// same scoutsync_dashboard.html that already lives in this repo and
// deploys to medsync.vet via GitHub Pages, without duplicating the
// codebase or splitting the Supabase backend. The dashboard's own JS
// still talks to the same Supabase project directly from the visitor's
// browser -- this Worker only proxies the HTML/asset request itself.
//
// Setup (one-time, in the Cloudflare dashboard):
//   1. Add the new domain to a free Cloudflare account, and point its
//      nameservers at Cloudflare (the registrar's dashboard will show
//      you how -- varies by registrar).
//   2. Workers & Pages -> Create Worker -> paste this file's contents in
//      as the Worker's script.
//   3. Workers & Pages -> (this Worker) -> Settings -> Triggers -> Custom
//      Domains -> add the new domain (e.g. scoutsync.vet, and
//      www.scoutsync.vet if you want both) -- Cloudflare provisions TLS
//      automatically.
//   4. Visit the new domain -- it should load the live ScoutSync
//      dashboard exactly as medsync.vet/scoutsync_dashboard.html does.
//
// No changes to this repo or its GitHub Pages deploy are needed -- this
// script is the only piece that lives outside version control (Cloudflare
// doesn't read from GitHub here), so it's kept here for reference/history
// only. If the Worker script ever needs updating, edit it in the
// Cloudflare dashboard and copy the change back into this file.

const UPSTREAM_ORIGIN = 'https://medsync.vet';
const DASHBOARD_PATH = '/scoutsync_dashboard.html';

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Root ("/") serves the dashboard directly, so the new domain reads
    // cleanly (https://scoutsync.vet/) instead of needing the .html path.
    // Any other path is passed straight through to the same file on
    // medsync.vet, in case something ever links to a specific path.
    const upstreamPath = url.pathname === '/' ? DASHBOARD_PATH : url.pathname;
    const upstreamUrl = UPSTREAM_ORIGIN + upstreamPath + url.search;

    const upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: request.headers,
    });

    // Clone so we can send back a response with our own domain reflected
    // in headers rather than any upstream-specific ones.
    const response = new Response(upstreamResponse.body, upstreamResponse);
    response.headers.set('X-Served-Via', 'scoutsync-cloudflare-proxy');
    return response;
  },
};
