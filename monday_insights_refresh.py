#!/usr/bin/env python3
"""
Monday morning insights refresh.
Queries Supabase for the 3 highest-dollar-impact findings across all locations,
updates the MANAGED-INSIGHTS block in index.html, then commits and pushes.
Runs via GitHub Actions every Monday at 8am CT.
"""

import json, time, urllib.request, urllib.error, sys
from datetime import date, timedelta

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2  # 2s, 4s between attempts


def _urlopen_with_retry(req, timeout):
    """Retries transient failures (5xx, connection resets, timeouts) with backoff.
    4xx errors are raised immediately -- retrying a bad request won't help.
    Without this, a single Supabase HTTP 500 or a dropped TLS connection killed
    the whole run outright instead of costing a few seconds."""
    last_err = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.status
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last_err = e
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < RETRY_ATTEMPTS:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"    transient error ({last_err}) — retrying in {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
            time.sleep(wait)
    raise last_err


SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3"
            "Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0"
            ".JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s")

LOC_NAMES = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}
WHEATON_VID = "28253"

H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}

today      = date.today()
days30_ago = (today - timedelta(days=30)).isoformat()
days60_fwd = (today + timedelta(days=60)).isoformat()
today_str  = today.isoformat()


def supa_get(path):
    req = urllib.request.Request(SUPA_URL + path, headers=H)
    try:
        body, _ = _urlopen_with_retry(req, timeout=30)
        data = json.loads(body)
        return data if isinstance(data, list) else []
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code} on {path[:80]}: {e.read().decode()[:120]}")
        return []
    except Exception as e:
        print(f"  Error fetching {path[:80]}: {e}")
        return []


def supa_get_paginated(path, page_size=1000):
    """Like supa_get(), but pages via limit/offset -- PostgREST silently caps
    a single request at its configured max-rows regardless of any limit=
    in the query string, and 30 days x 4 locations of encounters can
    exceed that."""
    out = []
    offset = 0
    sep = "&" if "?" in path else "?"
    while True:
        page = supa_get(f"{path}{sep}limit={page_size}&offset={offset}")
        if not page:
            return out
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


# Same keyword buckets as categorizeComplaint() in scoutsync_dashboard.html's
# "Billing Consistency by Provider" section -- kept in sync manually since
# this is a one-off Python port, not shared code.
COMPLAINT_CATEGORIES = [
    ("Vomiting / GI upset",         ["vomit", "diarrhea", "gi upset", "stomach", "nausea", "ate something", "ingest"]),
    ("Skin / Allergy / Ear",        ["skin", "itch", "allerg", "rash", "hot spot", "ear"]),
    ("Wound / Trauma / Limping",    ["wound", "laceration", "bite", "hit by car", "hbc", "trauma", "limp", "lame", "fracture", "broken"]),
    ("Respiratory",                 ["cough", "sneeze", "breathing", "respiratory", "wheez"]),
    ("Urinary / Reproductive",      ["urinary", "uti", "urinat", "blood in urine", "pregnan", "whelp", "labor"]),
    ("Lethargy / Not eating / Ill", ["lethargy", "not eating", "anorexia", "weak", "fever", "malaise"]),
    ("Dental",                      ["dental", "tooth", "teeth"]),
    ("Eye",                         ["eye", "conjunctiv"]),
    ("Wellness / Vaccine",          ["wellness", "vaccine", "annual", "checkup", "check up", "spay", "neuter"]),
]

# Same thresholds as BILLING_CONSISTENCY_MIN_N / _MIN_PROVIDERS / _HIGH_CV on
# the dashboard, so a category only surfaces here if it would also be
# flagged "High variance" there.
BILLING_MIN_N = 3
BILLING_MIN_PROVIDERS = 2
BILLING_HIGH_CV = 25


def categorize_complaint(text):
    t = (text or "").lower().strip()
    if not t:
        return "Unspecified"
    for label, kws in COMPLAINT_CATEGORIES:
        if any(k in t for k in kws):
            return label
    return "Other"


def stdev(values, mean):
    if len(values) < 2:
        return 0
    return (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def fmt_dollar(n):
    return f"${n:,.0f}"


def card_html(icon, icon_color, bg, border, icon_bg, title, body, badge, badge_cls, tag):
    return (
        f'      <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;'
        f'background:{bg};border:0.5px solid {border};border-radius:8px;">\n'
        f'        <div style="width:30px;height:30px;border-radius:7px;background:{icon_bg};'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;">\n'
        f'          <i class="ti {icon}" style="color:{icon_color};font-size:14px;" aria-hidden="true"></i>\n'
        f'        </div>\n'
        f'        <div style="flex:1;">\n'
        f'          <p style="font-size:12px;font-weight:500;color:#1C2B4A;margin-bottom:2px;">{title}</p>\n'
        f'          <p style="font-size:11px;color:#4A5568;line-height:1.5;">{body}</p>\n'
        f'        </div>\n'
        f'        <div style="text-align:right;flex-shrink:0;">\n'
        f'          <span class="badge {badge_cls}" style="font-size:11px;">{badge}</span>\n'
        f'          <p style="font-size:10px;color:#4A5568;margin-top:4px;">{tag}</p>\n'
        f'        </div>\n'
        f'      </div>'
    )


def build_insights():
    insights = []

    # ── 1. Top goods-lost location (last 30 days) ───────────────────────────
    gl = supa_get(
        f"/rest/v1/goods_lost?select=location_id,value_lost,product_name"
        f"&created_at=gte.{days30_ago}&order=value_lost.desc&limit=200"
    )
    if gl:
        by_loc = {}
        for r in gl:
            lid = r.get("location_id", "")
            by_loc[lid] = by_loc.get(lid, 0) + float(r.get("value_lost") or 0)
        if by_loc:
            top_lid, top_val = max(by_loc.items(), key=lambda x: x[1])
            loc_name = LOC_NAMES.get(top_lid, top_lid)
            count    = sum(1 for r in gl if r.get("location_id") == top_lid)
            top_prod = next((r["product_name"] for r in gl if r.get("location_id") == top_lid and r.get("product_name")), "")
            body     = f"{count} submission{'s' if count != 1 else ''} totaling {fmt_dollar(top_val)} in the last 30 days."
            if top_prod:
                body += f" Highest single item: {top_prod}."
            urgency = "bad" if top_val > 500 else "warn"
            insights.append({
                "dollar": top_val,
                "html": card_html(
                    icon="ti-alert-circle",
                    icon_color="#a33030" if urgency == "bad" else "#a0700a",
                    bg="#fff5f5" if urgency == "bad" else "#fdf8ee",
                    border="#f5c6c6" if urgency == "bad" else "#f0d070",
                    icon_bg="#fde8e8" if urgency == "bad" else "#fdefc7",
                    title=f"Goods lost — {loc_name} · top location this period",
                    body=body,
                    badge=fmt_dollar(top_val),
                    badge_cls="badge-bad" if urgency == "bad" else "badge-warn",
                    tag="Goods lost",
                ),
            })

    # ── 2. Most urgent expiring lot (next 60 days, all locations) ──────────
    lots = supa_get(
        f"/rest/v1/lots?select=expiration_date,qty_remaining,location_id,products(name)"
        f"&expiration_date=gte.{today_str}&expiration_date=lte.{days60_fwd}"
        f"&order=expiration_date.asc&limit=50"
    )
    if lots:
        lot = lots[0]
        exp      = lot.get("expiration_date", "")
        days_left= (date.fromisoformat(exp) - today).days if exp else 999
        prod_name= (lot.get("products") or {}).get("name", "Unknown product")
        qty      = lot.get("qty_remaining")
        loc_name = LOC_NAMES.get(lot.get("location_id", ""), "Unknown location")
        total_exp= len(lots)
        qty_txt  = f" · {qty} remaining" if qty is not None else ""
        body     = (f"Expires {exp}{qty_txt} · {days_left} days left · "
                    f"{total_exp} lot{'s' if total_exp != 1 else ''} expiring portfolio-wide within 60 days.")
        urgency  = "bad" if days_left <= 14 else "warn"
        est_loss = float(qty or 1) * 10  # rough estimate, no unit cost on lots table
        insights.append({
            "dollar": 10000 - days_left,  # rank by urgency
            "html": card_html(
                icon="ti-alert-triangle",
                icon_color="#a33030" if urgency == "bad" else "#a0700a",
                bg="#fff5f5" if urgency == "bad" else "#fdf8ee",
                border="#f5c6c6" if urgency == "bad" else "#f0d070",
                icon_bg="#fde8e8" if urgency == "bad" else "#fdefc7",
                title=f"Expiring soon — {prod_name} · {loc_name}",
                body=body,
                badge=f"{days_left}d",
                badge_cls="badge-bad" if urgency == "bad" else "badge-warn",
                tag="Expiring lot",
            ),
        })

    # ── 3. Top COGS driver across all locations (last 30 days) ─────────────
    di = supa_get(
        f"/rest/v1/dispensed_items?select=product_name,location_name,unit_cost,quantity"
        f"&dispensed_at=gte.{days30_ago}&sku=not.is.null&limit=2000"
    )
    if di:
        by_prod = {}
        for r in di:
            k    = r.get("product_name") or "Unknown"
            cost = float(r.get("unit_cost") or 0) * float(r.get("quantity") or 0)
            by_prod[k] = by_prod.get(k, 0) + cost
        if by_prod:
            top_prod, top_cost = max(by_prod.items(), key=lambda x: x[1])
            # Find which location uses it most
            loc_counts = {}
            for r in di:
                if r.get("product_name") == top_prod:
                    loc = r.get("location_name") or "Unknown"
                    loc_counts[loc] = loc_counts.get(loc, 0) + float(r.get("unit_cost") or 0) * float(r.get("quantity") or 0)
            top_loc = max(loc_counts, key=loc_counts.get) if loc_counts else "—"
            body = (f"{fmt_dollar(top_cost)} in dispensed cost over 30 days. "
                    f"Highest volume at {top_loc}. Verify par levels and review substitution options.")
            insights.append({
                "dollar": top_cost,
                "html": card_html(
                    icon="ti-pill",
                    icon_color="#a0700a",
                    bg="#fdf8ee",
                    border="#f0d070",
                    icon_bg="#fdefc7",
                    title=f"Top cost driver — {top_prod}",
                    body=body,
                    badge=fmt_dollar(top_cost),
                    badge_cls="badge-warn",
                    tag="Cost driver",
                ),
            })

    # ── 4. Billing variance by provider, same reason-for-visit category ────
    # Same directional analysis as "Billing Consistency by Provider" on the
    # Clinical Operations tab (encounters.chief_complaint bucketed by
    # keyword, invoice_total compared across doctors) -- only surfaces here
    # if a category's spread also clears the dashboard's own "High variance"
    # bar, so this and the dashboard section never disagree about what
    # counts as notable.
    UNATTRIBUTED_PROVIDER = "00000000-0000-0000-0000-000000000000"
    enc = supa_get_paginated(
        f"/rest/v1/encounters?select=provider_id,chief_complaint,invoice_total,started_at"
        f"&had_exam=eq.true&started_at=gte.{days30_ago}&started_at=lte.{today_str}"
    )
    if enc:
        providers = supa_get_paginated("/rest/v1/providers?select=id,full_name")
        name_by_id = {p["id"]: p["full_name"] for p in providers}

        by_category = {}  # label -> {provider_name: [invoice_total, ...]}
        for r in enc:
            cc, pid = (r.get("chief_complaint") or "").strip(), r.get("provider_id")
            if not cc or not pid or pid == UNATTRIBUTED_PROVIDER:
                continue
            cat = categorize_complaint(cc)
            name = name_by_id.get(pid, "Unknown provider")
            by_category.setdefault(cat, {}).setdefault(name, []).append(float(r.get("invoice_total") or 0))

        best = None  # highest-dollar-impact qualifying category
        for cat, by_provider in by_category.items():
            stats = []
            for name, values in by_provider.items():
                if len(values) < BILLING_MIN_N:
                    continue
                mean = sum(values) / len(values)
                stats.append({"name": name, "n": len(values), "mean": mean})
            if len(stats) < BILLING_MIN_PROVIDERS:
                continue
            means = [s["mean"] for s in stats]
            overall_mean = sum(means) / len(means)
            cv = (stdev(means, overall_mean) / overall_mean * 100) if overall_mean else 0
            if cv < BILLING_HIGH_CV:
                continue
            stats.sort(key=lambda s: s["mean"])
            low, high = stats[0], stats[-1]
            # What the lowest-charging doctor would have billed at the
            # category average, over their own case volume this period.
            est_impact = (overall_mean - low["mean"]) * low["n"]
            if est_impact <= 0:
                continue
            if best is None or est_impact > best["est_impact"]:
                best = {"cat": cat, "cv": cv, "low": low, "high": high,
                        "overall_mean": overall_mean, "providers": len(stats), "est_impact": est_impact}

        if best:
            body = (f"{best['cat']}: {best['providers']} doctors compared, {best['cv']:.0f}% spread. "
                    f"{best['low']['name']} averages {fmt_dollar(best['low']['mean'])}/case ({best['low']['n']} cases) "
                    f"vs. a {fmt_dollar(best['overall_mean'])} category average -- "
                    f"{fmt_dollar(best['est_impact'])} potential gap this period.")
            insights.append({
                "dollar": best["est_impact"],
                "html": card_html(
                    icon="ti-receipt-2",
                    icon_color="#a0700a",
                    bg="#fdf8ee",
                    border="#f0d070",
                    icon_bg="#fdefc7",
                    title=f"Billing variance — {best['cat']}",
                    body=body,
                    badge=fmt_dollar(best["est_impact"]),
                    badge_cls="badge-warn",
                    tag="Billing variance",
                ),
            })

    # Sort by dollar impact, take top 3
    insights.sort(key=lambda x: x["dollar"], reverse=True)
    return [i["html"] for i in insights[:3]]


def save_insights(cards):
    """Persist generated insight cards to Supabase so the portfolio page can cache them."""
    payload = json.dumps({"id": 1, "insights_html": cards, "refreshed_at": today_str}).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/organization_settings",
        data=payload,
        headers={
            **H,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    req.get_method = lambda: "POST"
    try:
        _, status = _urlopen_with_retry(req, timeout=30)
        print(f"  Saved {len(cards)} insight card(s) to Supabase (HTTP {status})")
    except urllib.error.HTTPError as e:
        print(f"  Warning: could not save to Supabase ({e.code}) — insights still generated for email")


if __name__ == "__main__":
    print(f"\n=== Monday Insights Refresh — {today_str} ===\n")
    print("Querying Supabase...")
    cards = build_insights()
    if not cards:
        print("  No insights generated — check Supabase data.")
        sys.exit(0)
    print(f"  {len(cards)} insight(s) generated.")
    save_insights(cards)
    print("\nDone.\n")
