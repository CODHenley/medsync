#!/usr/bin/env python3
"""
Monday morning insights refresh.
Queries Supabase for the 3 highest-dollar-impact findings across all locations,
updates the MANAGED-INSIGHTS block in index.html, then commits and pushes.
Runs via GitHub Actions every Monday at 8am CT.
"""

import json, urllib.request, urllib.error, re, subprocess, sys
from datetime import date, timedelta

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
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data if isinstance(data, list) else []
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code} on {path[:80]}: {e.read().decode()[:120]}")
        return []
    except Exception as e:
        print(f"  Error fetching {path[:80]}: {e}")
        return []


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
        f"/rest/v1/lots?select=expiration_date,quantity_remaining,location_id,products(name)"
        f"&expiration_date=gte.{today_str}&expiration_date=lte.{days60_fwd}"
        f"&order=expiration_date.asc&limit=50"
    )
    if lots:
        lot = lots[0]
        exp      = lot.get("expiration_date", "")
        days_left= (date.fromisoformat(exp) - today).days if exp else 999
        prod_name= (lot.get("products") or {}).get("name", "Unknown product")
        qty      = lot.get("quantity_remaining")
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

    # Sort by dollar impact, take top 3
    insights.sort(key=lambda x: x["dollar"], reverse=True)
    return [i["html"] for i in insights[:3]]


def update_html(cards):
    path = "index.html"
    with open(path, encoding="utf-8") as f:
        html = f.read()

    start_marker = "<!-- MANAGED-INSIGHTS-START -->"
    end_marker   = "<!-- MANAGED-INSIGHTS-END -->"
    start_idx = html.find(start_marker)
    end_idx   = html.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("ERROR: Could not find MANAGED-INSIGHTS markers in index.html")
        sys.exit(1)

    inner = "\n".join(cards)
    new_html = (
        html[:start_idx + len(start_marker)]
        + "\n"
        + inner
        + "\n      "
        + html[end_idx:]
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"  Updated {len(cards)} insight card(s) in index.html")


def git_commit_push():
    run = lambda *args: subprocess.run(args, check=True)
    result = subprocess.run(["git", "diff", "--staged", "--quiet"], capture_output=True)
    subprocess.run(["git", "add", "index.html"])
    result = subprocess.run(["git", "diff", "--staged", "--quiet"], capture_output=True)
    if result.returncode == 0:
        print("  No changes to commit — insights unchanged.")
        return
    run("git", "config", "user.name",  "MedSync Insights Bot")
    run("git", "config", "user.email", "bot@medsync.vet")
    run("git", "commit", "-m", f"chore: Monday insights refresh {today_str}")
    run("git", "push")
    print("  Committed and pushed.")


if __name__ == "__main__":
    print(f"\n=== Monday Insights Refresh — {today_str} ===\n")
    print("Querying Supabase...")
    cards = build_insights()
    if not cards:
        print("  No insights generated — check Supabase data.")
        sys.exit(0)
    print(f"  {len(cards)} insight(s) generated.")
    update_html(cards)
    git_commit_push()
    print("\nDone.\n")
