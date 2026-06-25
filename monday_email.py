#!/usr/bin/env python3
"""
Monday morning insights email — two flavors:
  - Inventory leads & managers : location-level insights + ordering focus
  - Admins                     : regional rollup + per-lead KPI scorecard

Only sends to users with email_insights_enabled = true (or null, treated as true).
Unsubscribe/resubscribe links use medsync_unsubscribe.html?uid=<id>&action=<action>.

Runs via GitHub Actions every Monday at 8:07am CT.
Requires: RESEND_API_KEY GitHub Actions secret.
"""

import json, os, sys, urllib.request, urllib.error
from datetime import date, timedelta

SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZH"
    "JteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0"
    ".JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
)
SITE_BASE    = "https://codhenley.github.io/medsync"
LOGIN_URL    = f"{SITE_BASE}/medsync_login.html"
UNSUB_BASE   = f"{SITE_BASE}/medsync_unsubscribe.html"
FROM_EMAIL   = "MedSync <insights@medsync.vet>"

H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}

today       = date.today()
week_label  = today.strftime("%B %d, %Y")
days7_ago   = (today - timedelta(days=7)).isoformat()
days30_ago  = (today - timedelta(days=30)).isoformat()
days14_fwd  = (today + timedelta(days=14)).isoformat()
days60_fwd  = (today + timedelta(days=60)).isoformat()
today_iso   = today.isoformat()

LOC_NAMES = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}

NAV  = "#1C2B4A"
GOLD = "#C8922A"
GREEN= "#2E8B57"
RED  = "#C0392B"
MIST = "#8A93A8"


# ── Supabase helpers ──────────────────────────────────────────────────────────

def supa_get(path):
    req = urllib.request.Request(SUPA_URL + path, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data if isinstance(data, list) else []
    except urllib.error.HTTPError as e:
        print(f"  Supabase {e.code} on {path[:80]}: {e.read().decode()[:120]}")
        return []
    except Exception as e:
        print(f"  Error on {path[:80]}: {e}")
        return []


def loc_name(lid):
    return LOC_NAMES.get(lid, "Unknown location")


def fmt_dollar(n):
    return f"${n:,.0f}"


# ── Recipients ────────────────────────────────────────────────────────────────

def get_recipients():
    """Return (admins, leads) lists — only users with email_insights_enabled != false."""
    users = supa_get(
        "/rest/v1/users?select=id,full_name,email,role,location_id,region_id"
        "&is_active=eq.true&email_insights_enabled=neq.false"
    )
    admins, leads = [], []
    seen = set()
    for u in users:
        em = (u.get("email") or "").strip().lower()
        if not em or em in seen:
            continue
        seen.add(em)
        role = u.get("role", "")
        if role == "admin":
            admins.append(u)
        elif role in ("inventory_lead", "manager"):
            leads.append(u)
    return admins, leads


# ── Data fetching ─────────────────────────────────────────────────────────────

def get_expiring_lots_14d():
    return supa_get(
        f"/rest/v1/lots?select=expiration_date,qty_remaining,location_id,products(name,category)"
        f"&expiration_date=gte.{today_iso}&expiration_date=lte.{days14_fwd}"
        f"&status=eq.Active&order=expiration_date.asc&limit=50"
    )

def get_expiring_lots_60d():
    return supa_get(
        f"/rest/v1/lots?select=expiration_date,qty_remaining,location_id,products(name)"
        f"&expiration_date=gte.{today_iso}&expiration_date=lte.{days60_fwd}"
        f"&status=eq.Active&order=expiration_date.asc&limit=100"
    )

def get_goods_lost_7d():
    return supa_get(
        f"/rest/v1/goods_lost?select=location_id,value_lost,product_name,created_at,submitted_by_user_id"
        f"&created_at=gte.{days7_ago}&order=value_lost.desc&limit=200"
    )

def get_goods_lost_30d():
    return supa_get(
        f"/rest/v1/goods_lost?select=location_id,value_lost,product_name,created_at,submitted_by_user_id"
        f"&created_at=gte.{days30_ago}&order=created_at.desc&limit=500"
    )

def get_all_active_lots():
    return supa_get(
        "/rest/v1/lots?select=qty_remaining,location_id,products(name,qty_min,category)"
        "&status=eq.Active&limit=1000"
    )

def get_pending_pos():
    return supa_get(
        "/rest/v1/purchase_orders?select=id,location_id,created_at,status,total_cost"
        "&status=in.(pending,submitted)&order=created_at.asc&limit=100"
    )

def get_unreceived_pos():
    cutoff = (today - timedelta(days=3)).isoformat()
    return supa_get(
        f"/rest/v1/purchase_orders?select=id,location_id,created_at,total_cost"
        f"&status=eq.submitted&created_at=lte.{cutoff}T00:00:00&limit=50"
    )

def get_cycle_counts_30d():
    return supa_get(
        f"/rest/v1/cycle_counts?select=location_id,completed_at,submitted_by_user_id,status"
        f"&completed_at=gte.{days30_ago}&limit=200"
    )

def get_locations():
    return supa_get("/rest/v1/locations?select=id,name,region_id&order=name&limit=100")

def get_regions():
    return supa_get("/rest/v1/regions?select=id,name&order=name&limit=50")


# ── HTML building blocks ──────────────────────────────────────────────────────

def unsub_link(uid):
    return f"{UNSUB_BASE}?uid={uid}&action=unsubscribe"

def resub_link(uid):
    return f"{UNSUB_BASE}?uid={uid}&action=resubscribe"

def email_shell(title, subtitle, header_icon, body_html, recipient_uid):
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F5F3FA;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
<table cellpadding="0" cellspacing="0" width="100%" style="background:#F5F3FA;padding:32px 16px;">
  <tr><td align="center">
    <table cellpadding="0" cellspacing="0" width="600" style="max-width:600px;">

      <!-- Header -->
      <tr>
        <td style="background:{NAV};border-radius:14px 14px 0 0;padding:24px 32px;">
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td>
                <div style="font-size:11px;font-weight:700;color:rgba(255,255,255,.5);
                            text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;">MedSync</div>
                <div style="font-size:22px;font-weight:700;color:#fff;">{title}</div>
                <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:4px;">{subtitle}</div>
              </td>
              <td align="right" valign="top">
                <div style="font-size:28px;">{header_icon}</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="background:#fff;padding:28px 32px;border-radius:0 0 14px 14px;">
          {body_html}
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="padding:20px 32px;text-align:center;">
          <div style="font-size:10px;color:{MIST};line-height:1.8;">
            MedSync · Scout Veterinary Urgent Care<br>
            <a href="{unsub_link(recipient_uid)}" style="color:{MIST};">Unsubscribe from weekly insights</a>
            &nbsp;·&nbsp;
            <a href="{LOGIN_URL}" style="color:{MIST};">Open MedSync</a>
          </div>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def section_hdr(title, subtitle=""):
    sub = f'<div style="font-size:11px;color:{MIST};margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return (f'<div style="font-size:11px;font-weight:700;color:{MIST};text-transform:uppercase;'
            f'letter-spacing:.06em;padding:20px 0 8px 0;">{title}</div>{sub}')


def insight_row(icon, title, detail, badge, badge_color):
    return f"""
<table cellpadding="0" cellspacing="0" width="100%"
       style="margin-bottom:10px;background:#F8F7FC;border-radius:10px;overflow:hidden;">
  <tr>
    <td style="padding:12px 16px;">
      <table cellpadding="0" cellspacing="0" width="100%"><tr>
        <td width="34" valign="top" style="padding-right:12px;">
          <div style="width:32px;height:32px;background:#EEEBf8;border-radius:8px;
                      text-align:center;line-height:32px;font-size:18px;">{icon}</div>
        </td>
        <td valign="top">
          <div style="font-size:13px;font-weight:600;color:{NAV};margin-bottom:2px;">{title}</div>
          <div style="font-size:12px;color:#4A5568;line-height:1.5;">{detail}</div>
        </td>
        <td width="72" align="right" valign="top" style="padding-left:8px;">
          <span style="display:inline-block;background:{badge_color}22;color:{badge_color};
                       font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;
                       white-space:nowrap;">{badge}</span>
        </td>
      </tr></table>
    </td>
  </tr>
</table>"""


def kpi_card(name, location, gl_count, gl_value, low_stock, unreceived, last_cycle):
    def pill(text, color):
        return (f'<span style="display:inline-block;background:{color}22;color:{color};'
                f'font-size:10px;font-weight:700;padding:2px 8px;border-radius:12px;">{text}</span>')

    gl_color  = RED if gl_value > 300 else (GOLD if gl_value > 0 else GREEN)
    ls_color  = RED if low_stock > 5 else (GOLD if low_stock > 0 else GREEN)
    po_color  = RED if unreceived > 0 else GREEN
    cyc_color = GREEN if last_cycle else GOLD

    return f"""
<table cellpadding="0" cellspacing="0" width="100%"
       style="margin-bottom:12px;border:0.5px solid #DDD9EC;border-radius:10px;overflow:hidden;">
  <tr>
    <td style="padding:14px 16px;border-bottom:0.5px solid #F0EEF8;">
      <div style="font-size:13px;font-weight:700;color:{NAV};">{name}</div>
      <div style="font-size:11px;color:{MIST};">{location}</div>
    </td>
  </tr>
  <tr>
    <td style="padding:10px 16px;">
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td style="padding:4px 0;font-size:12px;color:#4A5568;width:60%;">Goods lost this week</td>
          <td align="right">{pill(fmt_dollar(gl_value)+f' ({gl_count} submissions)', gl_color)}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;font-size:12px;color:#4A5568;">Items below minimum</td>
          <td align="right">{pill(f'{low_stock} items', ls_color)}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;font-size:12px;color:#4A5568;">Unreceived POs (&gt;3d)</td>
          <td align="right">{pill(f'{unreceived} open', po_color)}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;font-size:12px;color:#4A5568;">Last cycle count</td>
          <td align="right">{pill(last_cycle or 'None this month', cyc_color)}</td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""


def region_card(region_name, locs, gl_total, expiring_count, low_stock_count, unreceived_count):
    def stat(label, value, color=NAV):
        return (f'<td align="center" style="padding:0 12px;">'
                f'<div style="font-size:18px;font-weight:700;color:{color};">{value}</div>'
                f'<div style="font-size:10px;color:{MIST};margin-top:2px;">{label}</div></td>')

    gl_color = RED if gl_total > 500 else (GOLD if gl_total > 0 else GREEN)
    exp_color = RED if expiring_count > 3 else (GOLD if expiring_count > 0 else GREEN)

    loc_list = ", ".join(l.get("name","") for l in locs) if locs else "No locations"

    return f"""
<table cellpadding="0" cellspacing="0" width="100%"
       style="margin-bottom:14px;border:0.5px solid #DDD9EC;border-radius:10px;overflow:hidden;">
  <tr>
    <td style="background:{NAV};padding:10px 16px;">
      <div style="font-size:13px;font-weight:700;color:#fff;">{region_name}</div>
      <div style="font-size:10px;color:rgba(255,255,255,.5);">{loc_list}</div>
    </td>
  </tr>
  <tr>
    <td style="padding:14px 16px;">
      <table cellpadding="0" cellspacing="0" width="100%"><tr>
        {stat('Locations', len(locs))}
        {stat('Goods lost', fmt_dollar(gl_total), gl_color)}
        {stat('Expiring &lt;14d', expiring_count, exp_color)}
        {stat('Low stock', low_stock_count, GOLD if low_stock_count > 0 else GREEN)}
        {stat('Unreceived POs', unreceived_count, RED if unreceived_count > 0 else GREEN)}
      </tr></table>
    </td>
  </tr>
</table>"""


def cta_button(text=None, url=None):
    text = text or "Open MedSync"
    url  = url  or LOGIN_URL
    return f"""
<table cellpadding="0" cellspacing="0" width="100%" style="margin-top:28px;">
  <tr>
    <td align="center">
      <a href="{url}" style="display:inline-block;background:{NAV};color:#fff;font-size:14px;
                font-weight:700;padding:14px 40px;border-radius:10px;text-decoration:none;">
        {text} →
      </a>
    </td>
  </tr>
  <tr>
    <td align="center" style="padding-top:10px;">
      <div style="font-size:11px;color:{MIST};">Log in to review inventory and manage your locations.</div>
    </td>
  </tr>
</table>"""


# ── Lead / Manager email ──────────────────────────────────────────────────────

def build_lead_email(recipient, expiring_14, gl_7d, all_lots, unreceived, pending_pos, expiring_60):
    first = (recipient.get("full_name") or "").split()[0] or "there"
    uid   = recipient.get("id", "")

    # Aggregate data
    gl_total   = sum(float(r.get("value_lost") or 0) for r in gl_7d)
    exp_count  = len(expiring_14)
    low_items  = [r for r in all_lots
                  if (r.get("qty_remaining") or 0) < ((r.get("products") or {}).get("qty_min") or 0)
                  and (r.get("products") or {}).get("qty_min")]
    unrec_count = len(unreceived)

    # Summary bar
    parts = []
    if exp_count:   parts.append(f"<strong>{exp_count}</strong> lot{'s' if exp_count!=1 else ''} expiring within 14 days")
    if len(low_items): parts.append(f"<strong>{len(low_items)}</strong> items below minimum")
    if gl_total:    parts.append(f"<strong>{fmt_dollar(gl_total)}</strong> goods lost this week")
    summary = " &nbsp;·&nbsp; ".join(parts) if parts else "All clear — great week ahead."

    # Insights
    insights_html = ""
    if gl_7d:
        by_loc = {}
        for r in gl_7d:
            lid = r.get("location_id","")
            by_loc[lid] = by_loc.get(lid,0) + float(r.get("value_lost") or 0)
        top_lid, top_val = max(by_loc.items(), key=lambda x: x[1])
        insights_html += insight_row("⚠️",
            f"Goods lost — {loc_name(top_lid)} leads this week",
            f"{len(gl_7d)} submission{'s' if len(gl_7d)!=1 else ''} totaling {fmt_dollar(gl_total)} across all locations.",
            fmt_dollar(gl_total), RED)

    if expiring_14:
        lot  = expiring_14[0]
        exp  = lot.get("expiration_date","")
        days = (date.fromisoformat(exp) - today).days if exp else 999
        prod = (lot.get("products") or {}).get("name","Unknown product")
        insights_html += insight_row("⏰",
            f"Expiring soon — {prod}",
            f"Expires {exp} ({days} day{'s' if days!=1 else ''} away)"
            + (f" · {len(expiring_14)-1} more lot{'s' if len(expiring_14)>2 else ''} in this window." if len(expiring_14)>1 else ""),
            f"{days}d", RED if days <= 7 else GOLD)

    if low_items:
        prod = (low_items[0].get("products") or {}).get("name","Unknown")
        insights_html += insight_row("📉",
            f"Low stock — {prod} + {len(low_items)-1} other{'s' if len(low_items)>2 else ''}",
            f"{len(low_items)} item{'s' if len(low_items)!=1 else ''} below minimum threshold. Review before placing this week's order.",
            f"{len(low_items)} items", GOLD)

    if not insights_html:
        insights_html = '<p style="font-size:12px;color:#888;padding:12px 0;">No significant findings this week.</p>'

    # Tasks
    tasks_html = ""
    if unreceived:
        oldest = unreceived[0]
        age = (today - date.fromisoformat(oldest["created_at"][:10])).days
        tasks_html += f'<tr><td style="padding:8px 0;border-bottom:1px solid #F0EEF8;font-size:13px;color:{NAV};"><span style="margin-right:8px;">📦</span><strong>{len(unreceived)} unreceived PO{"s" if len(unreceived)!=1 else ""}</strong> — oldest is {age} days old</td></tr>'
    if expiring_14:
        tasks_html += f'<tr><td style="padding:8px 0;border-bottom:1px solid #F0EEF8;font-size:13px;color:{NAV};"><span style="margin-right:8px;">🗑️</span><strong>Review {len(expiring_14)} expiring lot{"s" if len(expiring_14)!=1 else ""}</strong> — write off or transfer this week</td></tr>'
    if low_items:
        tasks_html += f'<tr><td style="padding:8px 0;border-bottom:1px solid #F0EEF8;font-size:13px;color:{NAV};"><span style="margin-right:8px;">🛒</span><strong>Restock {len(low_items)} item{"s" if len(low_items)!=1 else ""}</strong> below minimum — add to this week\'s order</td></tr>'
    if pending_pos:
        tasks_html += f'<tr><td style="padding:8px 0;font-size:13px;color:{NAV};"><span style="margin-right:8px;">✅</span><strong>{len(pending_pos)} draft order{"s" if len(pending_pos)!=1 else ""}</strong> awaiting submission</td></tr>'
    if not tasks_html:
        tasks_html = f'<tr><td style="padding:12px 0;font-size:12px;color:#888;">No pending tasks — nice work.</td></tr>'

    # Ordering focus
    ordering_html = ""
    seen_prods = set()
    for r in low_items[:5]:
        prod = (r.get("products") or {}).get("name","")
        if not prod or prod in seen_prods: continue
        seen_prods.add(prod)
        qty_r = r.get("qty_remaining",0)
        qty_m = (r.get("products") or {}).get("qty_min",0)
        ordering_html += f'<tr><td style="padding:8px 12px;border-bottom:1px solid #F0EEF8;font-size:13px;"><span style="display:inline-block;width:8px;height:8px;background:{RED};border-radius:50%;margin-right:10px;vertical-align:middle;"></span><strong>{prod}</strong><span style="color:{MIST};font-size:11px;margin-left:8px;">{qty_r} on hand · min {qty_m}</span></td></tr>'
    for r in expiring_60[:5]:
        prod = (r.get("products") or {}).get("name","")
        if not prod or prod in seen_prods: continue
        seen_prods.add(prod)
        exp  = r.get("expiration_date","")
        days = (date.fromisoformat(exp) - today).days if exp else 999
        ordering_html += f'<tr><td style="padding:8px 12px;border-bottom:1px solid #F0EEF8;font-size:13px;"><span style="display:inline-block;width:8px;height:8px;background:{GOLD};border-radius:50%;margin-right:10px;vertical-align:middle;"></span><strong>{prod}</strong><span style="color:{MIST};font-size:11px;margin-left:8px;">Expires in {days} days — order replacement</span></td></tr>'
    if not ordering_html:
        ordering_html = f'<tr><td style="padding:10px 12px;font-size:12px;color:#888;">No specific priorities this week.</td></tr>'

    body = f"""
<p style="font-size:14px;color:{NAV};margin:0 0 4px 0;">Hi {first},</p>
<p style="font-size:13px;color:#4A5568;line-height:1.6;margin:0 0 6px 0;">Here's your weekly inventory snapshot for <strong>{week_label}</strong>.</p>
<div style="background:{GOLD};border-radius:8px;padding:10px 16px;margin-bottom:20px;">
  <div style="font-size:12px;color:#fff;">{summary}</div>
</div>

{section_hdr("Key insights", "Highest-impact findings this week")}
{insights_html}

{section_hdr("Upcoming tasks")}
<table cellpadding="0" cellspacing="0" width="100%"
       style="border:0.5px solid #DDD9EC;border-radius:10px;overflow:hidden;margin-bottom:4px;">
  {tasks_html}
</table>

{section_hdr("Ordering focus", "Items to prioritize in this week's order")}
<table cellpadding="0" cellspacing="0" width="100%"
       style="background:#F8F7FC;border-radius:10px;overflow:hidden;">
  {ordering_html}
</table>

{cta_button()}
"""
    return email_shell(
        title="Monday Insights",
        subtitle=week_label,
        header_icon="📋",
        body_html=body,
        recipient_uid=uid,
    )


# ── Admin email ───────────────────────────────────────────────────────────────

def build_admin_email(recipient, locations, regions, gl_7d, gl_30d,
                      expiring_14, all_lots, unreceived, cycle_counts, leads):
    first = (recipient.get("full_name") or "").split()[0] or "there"
    uid   = recipient.get("id","")

    # ── Regional rollup ───────────────────────────────────────────────────────
    reg_by_id  = {r["id"]: r for r in regions}
    locs_by_reg = {}
    for l in locations:
        rid = l.get("region_id") or "__none__"
        locs_by_reg.setdefault(rid, []).append(l)

    # Pre-compute per-location aggregates
    gl_by_loc = {}
    for r in gl_7d:
        lid = r.get("location_id","")
        gl_by_loc[lid] = gl_by_loc.get(lid,0) + float(r.get("value_lost") or 0)

    exp_by_loc = {}
    for r in expiring_14:
        lid = r.get("location_id","")
        exp_by_loc[lid] = exp_by_loc.get(lid,0) + 1

    low_by_loc = {}
    for r in all_lots:
        prod    = r.get("products") or {}
        qty_r   = r.get("qty_remaining") or 0
        qty_min = prod.get("qty_min") or 0
        if qty_min and qty_r < qty_min:
            lid = r.get("location_id","")
            low_by_loc[lid] = low_by_loc.get(lid,0) + 1

    unrec_by_loc = {}
    for r in unreceived:
        lid = r.get("location_id","")
        unrec_by_loc[lid] = unrec_by_loc.get(lid,0) + 1

    regions_html = ""
    for reg in sorted(regions, key=lambda x: x.get("name","")):
        rid  = reg["id"]
        locs = locs_by_reg.get(rid, [])
        if not locs: continue
        gl_tot  = sum(gl_by_loc.get(l["id"],0) for l in locs)
        exp_cnt = sum(exp_by_loc.get(l["id"],0) for l in locs)
        low_cnt = sum(low_by_loc.get(l["id"],0) for l in locs)
        unr_cnt = sum(unrec_by_loc.get(l["id"],0) for l in locs)
        regions_html += region_card(reg["name"], locs, gl_tot, exp_cnt, low_cnt, unr_cnt)

    if not regions_html:
        regions_html = '<p style="font-size:12px;color:#888;padding:12px 0;">No regional data available.</p>'

    # ── Lead KPI scorecards ───────────────────────────────────────────────────
    # Build per-lead metrics using location-level data
    # For goods lost: match by location_id
    # For cycle counts: find most recent completed
    cyc_by_loc = {}
    for c in cycle_counts:
        lid = c.get("location_id","")
        if c.get("status") == "completed" and c.get("completed_at"):
            prev = cyc_by_loc.get(lid)
            if not prev or c["completed_at"] > prev:
                cyc_by_loc[lid] = c["completed_at"]

    kpis_html = ""
    for lead in sorted(leads, key=lambda x: x.get("full_name","")):
        lid      = lead.get("location_id","")
        lname    = loc_name(lid)
        gl_cnt   = sum(1 for r in gl_7d if r.get("location_id")==lid)
        gl_val   = gl_by_loc.get(lid,0)
        low_cnt  = low_by_loc.get(lid,0)
        unr_cnt  = unrec_by_loc.get(lid,0)
        last_cyc = cyc_by_loc.get(lid,"")
        last_cyc_label = last_cyc[:10] if last_cyc else ""
        kpis_html += kpi_card(
            name      = lead.get("full_name") or lead.get("email","Unknown"),
            location  = lname,
            gl_count  = gl_cnt,
            gl_value  = gl_val,
            low_stock = low_cnt,
            unreceived= unr_cnt,
            last_cycle= last_cyc_label,
        )

    if not kpis_html:
        kpis_html = '<p style="font-size:12px;color:#888;padding:12px 0;">No inventory leads found.</p>'

    # ── Portfolio-wide summary numbers ────────────────────────────────────────
    total_gl_7d  = sum(float(r.get("value_lost") or 0) for r in gl_7d)
    total_gl_30d = sum(float(r.get("value_lost") or 0) for r in gl_30d)
    total_exp14  = len(expiring_14)
    total_low    = sum(low_by_loc.values())
    total_unr    = len(unreceived)

    body = f"""
<p style="font-size:14px;color:{NAV};margin:0 0 4px 0;">Hi {first},</p>
<p style="font-size:13px;color:#4A5568;line-height:1.6;margin:0 0 20px 0;">
  Here's your admin summary for the week of <strong>{week_label}</strong>.
</p>

<!-- Portfolio snapshot -->
<table cellpadding="0" cellspacing="0" width="100%"
       style="background:#F8F7FC;border-radius:10px;margin-bottom:24px;">
  <tr>
    <td align="center" style="padding:16px 8px;">
      <table cellpadding="0" cellspacing="0"><tr>
        <td align="center" style="padding:0 16px;border-right:1px solid #DDD9EC;">
          <div style="font-size:20px;font-weight:700;color:{RED};">{fmt_dollar(total_gl_7d)}</div>
          <div style="font-size:10px;color:{MIST};margin-top:2px;">Goods lost this week</div>
        </td>
        <td align="center" style="padding:0 16px;border-right:1px solid #DDD9EC;">
          <div style="font-size:20px;font-weight:700;color:{GOLD};">{total_exp14}</div>
          <div style="font-size:10px;color:{MIST};margin-top:2px;">Lots expiring &lt;14d</div>
        </td>
        <td align="center" style="padding:0 16px;border-right:1px solid #DDD9EC;">
          <div style="font-size:20px;font-weight:700;color:{GOLD};">{total_low}</div>
          <div style="font-size:10px;color:{MIST};margin-top:2px;">Items below min</div>
        </td>
        <td align="center" style="padding:0 16px;">
          <div style="font-size:20px;font-weight:700;color:{"#C0392B" if total_unr else NAV};">{total_unr}</div>
          <div style="font-size:10px;color:{MIST};margin-top:2px;">Unreceived POs</div>
        </td>
      </tr></table>
    </td>
  </tr>
</table>

{section_hdr("Regional overview", "Key metrics by region this week")}
{regions_html}

{section_hdr("Inventory lead performance", "KPIs for each lead — week of " + week_label)}
{kpis_html}

{cta_button("Open MedSync Admin")}
"""
    return email_shell(
        title="Admin Weekly Summary",
        subtitle=week_label,
        header_icon="🏥",
        body_html=body,
        recipient_uid=uid,
    )


# ── Email send ────────────────────────────────────────────────────────────────

def send_email(resend_key, to_email, subject, html):
    payload = json.dumps({"from": FROM_EMAIL, "to": [to_email], "subject": subject, "html": html}).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            print(f"  ✓ {to_email} (id: {result.get('id','')})")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ✗ {to_email}: {e.code} {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"  ✗ {to_email}: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    resend_key = os.environ.get("RESEND_API_KEY","").strip()
    if not resend_key:
        print("ERROR: RESEND_API_KEY not set."); sys.exit(1)

    print(f"\n=== Monday Email — {today_iso} ===\n")

    admins, leads = get_recipients()
    print(f"  {len(admins)} admin(s), {len(leads)} lead(s)/manager(s)")
    if not admins and not leads:
        print("  No recipients — nothing to send."); sys.exit(0)

    # Fetch shared data once
    print("  Fetching data…")
    locations   = get_locations()
    regions     = get_regions()
    expiring_14 = get_expiring_lots_14d()
    expiring_60 = get_expiring_lots_60d()
    gl_7d       = get_goods_lost_7d()
    gl_30d      = get_goods_lost_30d()
    all_lots    = get_all_active_lots()
    pending_pos = get_pending_pos()
    unreceived  = get_unreceived_pos()
    cycle_counts= get_cycle_counts_30d()
    print(f"  Data ready.")

    sent = 0

    # Inventory leads & managers
    print(f"\n── Lead/Manager emails ──")
    for u in leads:
        email = u.get("email","")
        if not email: continue
        html = build_lead_email(u, expiring_14, gl_7d, all_lots, unreceived, pending_pos, expiring_60)
        if send_email(resend_key, email, f"MedSync Weekly Insights — {week_label}", html):
            sent += 1

    # Admins
    print(f"\n── Admin emails ──")
    for u in admins:
        email = u.get("email","")
        if not email: continue
        html = build_admin_email(u, locations, regions, gl_7d, gl_30d,
                                 expiring_14, all_lots, unreceived, cycle_counts, leads)
        if send_email(resend_key, email, f"MedSync Admin Summary — {week_label}", html):
            sent += 1

    total = len(leads) + len(admins)
    print(f"\nDone — {sent}/{total} email(s) sent.\n")


if __name__ == "__main__":
    main()
