#!/usr/bin/env python3
"""
Monday morning insights email.
Queries Supabase for inventory leads, builds a rich HTML email with key insights,
upcoming tasks, and ordering focus areas, then sends via Resend.

Runs via GitHub Actions every Monday at 8:07am CT, after the insights refresh.
Requires:
  RESEND_API_KEY  — GitHub Actions secret
  SUPA_KEY        — already embedded (anon key, read-only)
"""

import json, os, sys, urllib.request, urllib.error
from datetime import date, timedelta

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZH"
    "JteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0"
    ".JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
)
MEDSYNC_URL = "https://codhenley.github.io/medsync/medsync_login.html"
FROM_EMAIL  = "MedSync <insights@medsync.vet>"

H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}

today       = date.today()
week_label  = today.strftime("%B %d, %Y")
days30_ago  = (today - timedelta(days=30)).isoformat()
days7_ago   = (today - timedelta(days=7)).isoformat()
days14_fwd  = (today + timedelta(days=14)).isoformat()
days60_fwd  = (today + timedelta(days=60)).isoformat()
today_iso   = today.isoformat()

LOC_NAMES = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}


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


def loc(lid):
    return LOC_NAMES.get(lid, "Unknown location")


def fmt_dollar(n):
    return f"${n:,.0f}"


# ── Data gathering ────────────────────────────────────────────────────────────

def get_inventory_leads():
    users = supa_get(
        "/rest/v1/users?select=full_name,email,location_id"
        "&role=eq.inventory_lead&is_active=eq.true"
    )
    # Also include admins and managers so they stay informed
    admins = supa_get(
        "/rest/v1/users?select=full_name,email,location_id"
        "&role=in.(admin,manager)&is_active=eq.true"
    )
    seen, result = set(), []
    for u in (users + admins):
        em = (u.get("email") or "").strip().lower()
        if em and em not in seen:
            seen.add(em)
            result.append(u)
    return result


def get_expiring_lots():
    return supa_get(
        f"/rest/v1/lots?select=expiration_date,qty_remaining,location_id,product_id,products(name,category)"
        f"&expiration_date=gte.{today_iso}&expiration_date=lte.{days14_fwd}"
        f"&status=eq.Active&order=expiration_date.asc&limit=20"
    )


def get_expiring_soon_lots():
    """60-day window for the ordering focus section."""
    return supa_get(
        f"/rest/v1/lots?select=expiration_date,qty_remaining,location_id,products(name)"
        f"&expiration_date=gte.{today_iso}&expiration_date=lte.{days60_fwd}"
        f"&status=eq.Active&order=expiration_date.asc&limit=50"
    )


def get_low_stock():
    """Products where qty_remaining < qty_min."""
    return supa_get(
        "/rest/v1/lots?select=qty_remaining,location_id,product_id,products(name,qty_min,category)"
        "&status=eq.Active&limit=500"
    )


def get_recent_goods_lost():
    return supa_get(
        f"/rest/v1/goods_lost?select=location_id,value_lost,product_name,created_at"
        f"&created_at=gte.{days7_ago}&order=value_lost.desc&limit=100"
    )


def get_pending_orders():
    return supa_get(
        "/rest/v1/purchase_orders?select=id,location_id,created_at,status,total_cost"
        "&status=in.(pending,submitted)&order=created_at.asc&limit=50"
    )


def get_unreceived_pos():
    """POs submitted more than 3 days ago still not received."""
    cutoff = (today - timedelta(days=3)).isoformat()
    return supa_get(
        f"/rest/v1/purchase_orders?select=id,location_id,created_at,total_cost"
        f"&status=eq.submitted&created_at=lte.{cutoff}T00:00:00&limit=30"
    )


# ── Email HTML builder ────────────────────────────────────────────────────────

NAV   = "#1C2B4A"
GOLD  = "#C8922A"
GREEN = "#2E8B57"
RED   = "#C0392B"
MIST  = "#8A93A8"

def tag(color, text):
    bg_map = {RED: "#FEF0F0", GOLD: "#FEF3E2", GREEN: "#E8F5EE"}
    bg = bg_map.get(color, "#F0EEF8")
    return (f'<span style="display:inline-block;background:{bg};color:{color};'
            f'font-size:10px;font-weight:700;padding:2px 8px;border-radius:12px;">{text}</span>')


def insight_row(icon, title, detail, badge_text, badge_color):
    return f"""
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #F0EEF8;">
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td width="32" valign="top" style="padding-right:12px;">
              <div style="width:32px;height:32px;background:#F5F3FA;border-radius:8px;
                          text-align:center;line-height:32px;font-size:18px;">{icon}</div>
            </td>
            <td valign="top">
              <div style="font-size:13px;font-weight:600;color:{NAV};margin-bottom:3px;">{title}</div>
              <div style="font-size:12px;color:#4A5568;line-height:1.5;">{detail}</div>
            </td>
            <td width="80" valign="top" align="right">
              <span style="display:inline-block;background:{badge_color}22;color:{badge_color};
                           font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">{badge_text}</span>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def task_row(icon, title, detail, cta_text="#"):
    return f"""
    <tr>
      <td style="padding:8px 0;border-bottom:1px solid #F0EEF8;">
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td width="24" valign="top" style="padding-right:10px;font-size:16px;">{icon}</td>
            <td valign="middle">
              <div style="font-size:13px;font-weight:600;color:{NAV};">{title}</div>
              <div style="font-size:11px;color:{MIST};">{detail}</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def ordering_row(product, note, priority_color=GOLD):
    return f"""
    <tr>
      <td style="padding:8px 12px;border-bottom:1px solid #F0EEF8;">
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td width="8" style="padding-right:12px;">
              <div style="width:8px;height:8px;background:{priority_color};border-radius:50%;margin-top:4px;"></div>
            </td>
            <td>
              <div style="font-size:13px;font-weight:600;color:{NAV};">{product}</div>
              <div style="font-size:11px;color:#4A5568;">{note}</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def section_header(title, subtitle=""):
    sub_html = f'<div style="font-size:11px;color:{MIST};margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return f"""
    <tr>
      <td style="padding:24px 0 10px 0;">
        <div style="font-size:11px;font-weight:700;color:{MIST};text-transform:uppercase;
                    letter-spacing:0.06em;">{title}</div>
        {sub_html}
      </td>
    </tr>"""


def build_email_html(recipient_name, insights_rows, task_rows, ordering_rows,
                     expiring_count, low_stock_count, gl_this_week):
    first = recipient_name.split()[0] if recipient_name else "there"
    summary_parts = []
    if expiring_count:
        summary_parts.append(f"<strong>{expiring_count}</strong> lot{'s' if expiring_count != 1 else ''} expiring within 14 days")
    if low_stock_count:
        summary_parts.append(f"<strong>{low_stock_count}</strong> item{'s' if low_stock_count != 1 else ''} below minimum stock")
    if gl_this_week:
        summary_parts.append(f"<strong>{fmt_dollar(gl_this_week)}</strong> in goods lost this week")
    summary = " · ".join(summary_parts) if summary_parts else "All systems normal — great week ahead."

    insights_html  = "".join(insights_rows)  if insights_rows  else "<tr><td style='padding:12px 0;font-size:12px;color:#888;'>No significant findings this week.</td></tr>"
    tasks_html     = "".join(task_rows)      if task_rows      else "<tr><td style='padding:12px 0;font-size:12px;color:#888;'>No pending tasks.</td></tr>"
    ordering_html  = "".join(ordering_rows)  if ordering_rows  else "<tr><td style='padding:10px 12px;font-size:12px;color:#888;'>No specific ordering priorities this week.</td></tr>"

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
                <div style="font-size:22px;font-weight:700;color:#fff;">Monday Insights</div>
                <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:4px;">{week_label}</div>
              </td>
              <td align="right" valign="top">
                <div style="font-size:28px;">📋</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Summary bar -->
      <tr>
        <td style="background:{GOLD};padding:10px 32px;">
          <div style="font-size:12px;color:#fff;">{summary}</div>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="background:#fff;padding:24px 32px;border-radius:0 0 14px 14px;">

          <!-- Greeting -->
          <p style="font-size:14px;color:{NAV};margin:0 0 4px 0;">Hi {first},</p>
          <p style="font-size:13px;color:#4A5568;line-height:1.6;margin:0 0 20px 0;">
            Here's your weekly inventory snapshot. Below are the key items to review before
            placing this week's order.
          </p>

          <!-- Key Insights -->
          <table cellpadding="0" cellspacing="0" width="100%">
            {section_header("Key insights", "Highest-impact findings across all locations")}
            {insights_html}
          </table>

          <!-- Upcoming Tasks -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin-top:8px;">
            {section_header("Upcoming tasks", "Actions requiring attention this week")}
            {tasks_html}
          </table>

          <!-- Ordering Focus -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin-top:8px;">
            {section_header("Ordering focus", "Items to prioritize when building this week's order")}
            <tr>
              <td style="background:#F8F7FC;border-radius:10px;overflow:hidden;padding:0;">
                <table cellpadding="0" cellspacing="0" width="100%">
                  {ordering_html}
                </table>
              </td>
            </tr>
          </table>

          <!-- CTA -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin-top:32px;">
            <tr>
              <td align="center">
                <a href="{MEDSYNC_URL}"
                   style="display:inline-block;background:{NAV};color:#fff;font-size:14px;
                          font-weight:700;padding:14px 40px;border-radius:10px;
                          text-decoration:none;letter-spacing:.01em;">
                  Open MedSync →
                </a>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding-top:10px;">
                <div style="font-size:11px;color:{MIST};">
                  Log in to review inventory, submit orders, and manage your locations.
                </div>
              </td>
            </tr>
          </table>

        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="padding:20px 32px;text-align:center;">
          <div style="font-size:10px;color:{MIST};line-height:1.6;">
            MedSync · Scout Veterinary Urgent Care<br>
            You're receiving this because you're an inventory lead or manager in MedSync.<br>
            Questions? Reply to this email or contact <a href="mailto:mhenley@scoutcare.com"
              style="color:{MIST};">mhenley@scoutcare.com</a>
          </div>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not resend_key:
        print("ERROR: RESEND_API_KEY not set — skipping email send.")
        sys.exit(1)

    print(f"\n=== Monday Email — {today_iso} ===\n")

    # Recipients
    leads = get_inventory_leads()
    if not leads:
        print("  No inventory leads/admins found in users table — nothing to send.")
        sys.exit(0)
    print(f"  {len(leads)} recipient(s): {', '.join(u.get('email','') for u in leads)}")

    # Data
    expiring     = get_expiring_lots()
    expiring_60  = get_expiring_soon_lots()
    all_lots     = get_low_stock()
    gl_week      = get_recent_goods_lost()
    pending_pos  = get_pending_orders()
    unreceived   = get_unreceived_pos()

    # ── Insights section ──────────────────────────────────────────────────────
    insights = []

    # Goods lost this week
    gl_total = sum(float(r.get("value_lost") or 0) for r in gl_week)
    if gl_week:
        by_loc = {}
        for r in gl_week:
            lid = r.get("location_id", "")
            by_loc[lid] = by_loc.get(lid, 0) + float(r.get("value_lost") or 0)
        top_lid = max(by_loc, key=by_loc.get)
        top_val = by_loc[top_lid]
        count   = len(gl_week)
        insights.append((top_val, insight_row(
            "⚠️", f"Goods lost — {loc(top_lid)} leads this week",
            f"{count} submission{'s' if count!=1 else ''} totaling {fmt_dollar(gl_total)} "
            f"across all locations. {loc(top_lid)} accounts for {fmt_dollar(top_val)}.",
            fmt_dollar(gl_total), RED,
        )))

    # Critical expiries (within 14 days)
    if expiring:
        lot = expiring[0]
        exp  = lot.get("expiration_date", "")
        days = (date.fromisoformat(exp) - today).days if exp else 999
        prod = (lot.get("products") or {}).get("name", "Unknown product")
        qty  = lot.get("qty_remaining")
        insights.append((10000 - days, insight_row(
            "⏰", f"Expiring within 14 days — {prod}",
            f"Expires {exp}, {days} day{'s' if days!=1 else ''} from today"
            + (f", {qty} units remaining" if qty else "")
            + f" · {loc(lot.get('location_id',''))}."
            + (f" Plus {len(expiring)-1} more lot{'s' if len(expiring)>2 else ''} in this window." if len(expiring)>1 else ""),
            f"{days}d", RED if days <= 7 else GOLD,
        )))

    # Low stock items
    low_stock_items = []
    for r in all_lots:
        prod = r.get("products") or {}
        qty_rem = r.get("qty_remaining")
        qty_min = prod.get("qty_min")
        if qty_rem is not None and qty_min and float(qty_rem) < float(qty_min):
            low_stock_items.append(r)
    if low_stock_items:
        sample = low_stock_items[0]
        prod = (sample.get("products") or {})
        insights.append((len(low_stock_items) * 100, insight_row(
            "📉", f"Low stock — {prod.get('name','Unknown')} and {len(low_stock_items)-1} other{'s' if len(low_stock_items)>2 else ''}",
            f"{len(low_stock_items)} item{'s' if len(low_stock_items)!=1 else ''} below minimum threshold. "
            f"Review before submitting this week's order.",
            f"{len(low_stock_items)} items", GOLD,
        )))

    insights.sort(key=lambda x: x[0], reverse=True)
    insight_rows = [r for _, r in insights[:4]]

    # ── Tasks section ─────────────────────────────────────────────────────────
    tasks = []
    if unreceived:
        oldest = unreceived[0]
        age = (today - date.fromisoformat(oldest["created_at"][:10])).days
        tasks.append(task_row(
            "📦",
            f"{len(unreceived)} unreceived PO{'s' if len(unreceived)!=1 else ''}",
            f"Oldest submitted {age} days ago at {loc(oldest.get('location_id',''))} — confirm receipt in MedSync.",
        ))
    if expiring:
        tasks.append(task_row(
            "🗑️",
            f"Review {len(expiring)} expiring lot{'s' if len(expiring)!=1 else ''} — write off or transfer",
            f"All expiring within 14 days. Log disposal in Goods Lost before end of week.",
        ))
    if low_stock_items:
        tasks.append(task_row(
            "🛒",
            f"Restock {len(low_stock_items)} item{'s' if len(low_stock_items)!=1 else ''} below minimum",
            "Add to this week's order — check par levels in the Weekly Order screen.",
        ))
    if pending_pos:
        tasks.append(task_row(
            "✅",
            f"{len(pending_pos)} order{'s' if len(pending_pos)!=1 else ''} awaiting submission",
            f"Draft PO{'s' if len(pending_pos)!=1 else ''} in MedSync — review and submit before Vetcove cutoff.",
        ))
    if not tasks:
        tasks.append(task_row("✅", "No critical tasks this week", "Nice work — all caught up."))

    # ── Ordering focus section ────────────────────────────────────────────────
    ordering = []

    # Priority 1: items below min stock
    for r in low_stock_items[:5]:
        prod   = r.get("products") or {}
        name   = prod.get("name") or "Unknown"
        qty_r  = r.get("qty_remaining", 0)
        qty_m  = prod.get("qty_min", 0)
        l_name = loc(r.get("location_id", ""))
        ordering.append((float(qty_m or 0) - float(qty_r or 0), ordering_row(
            name,
            f"Currently {qty_r} on hand, minimum is {qty_m} · {l_name}",
            RED,
        )))

    # Priority 2: items expiring in 60 days (need reorder)
    seen_prods = {(r.get("products") or {}).get("name") for _, _ in ordering for r in low_stock_items[:5]}
    for r in expiring_60:
        prod = (r.get("products") or {}).get("name", "")
        if not prod or prod in seen_prods:
            continue
        exp  = r.get("expiration_date","")
        days = (date.fromisoformat(exp) - today).days if exp else 999
        l_name = loc(r.get("location_id",""))
        ordering.append((days, ordering_row(
            prod,
            f"Lot expires in {days} days — consider ordering replacement stock · {l_name}",
            GOLD,
        )))
        seen_prods.add(prod)
        if len(ordering) >= 8:
            break

    ordering.sort(key=lambda x: x[0])
    ordering_rows = [r for _, r in ordering[:6]]

    # ── Send emails ───────────────────────────────────────────────────────────
    sent = 0
    for u in leads:
        email   = u.get("email", "")
        name    = u.get("full_name") or email.split("@")[0].replace(".", " ").title()
        if not email:
            continue

        html = build_email_html(
            recipient_name  = name,
            insights_rows   = insight_rows,
            task_rows       = tasks,
            ordering_rows   = ordering_rows,
            expiring_count  = len(expiring),
            low_stock_count = len(low_stock_items),
            gl_this_week    = gl_total,
        )

        payload = json.dumps({
            "from":    FROM_EMAIL,
            "to":      [email],
            "subject": f"MedSync Weekly Insights — {week_label}",
            "html":    html,
        }).encode()

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {resend_key}",
                "Content-Type":  "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())
                print(f"  ✓ Sent to {email} (id: {result.get('id','')})")
                sent += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            print(f"  ✗ Failed to send to {email}: {e.code} {body}")
        except Exception as e:
            print(f"  ✗ Error sending to {email}: {e}")

    print(f"\nDone — {sent}/{len(leads)} email(s) sent.\n")


if __name__ == "__main__":
    main()
