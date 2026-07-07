import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

const ADMIN_EMAIL = 'mhenley@scoutcare.com'
const FROM_EMAIL  = 'medsync@medsync.vet'

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const body = await req.json()
    const {
      scanned_value,
      fda_brand_name,
      fda_generic_name,
      fda_labeler,
      qty_received,
      lot_number,
      expiry,
      unit_cost,
      notes,
      po_ref,
      location_id,
      location_name,
      receiver_name,
      receiver_email,
    } = body

    if (!scanned_value && !fda_brand_name && !fda_generic_name) {
      return new Response(JSON.stringify({ error: 'At least one of scanned_value, fda_brand_name, or fda_generic_name is required' }), { status: 400, headers: CORS })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    // 1. Save to pending_receipts
    const { data: row, error: dbErr } = await supabase
      .from('pending_receipts')
      .insert({
        scanned_value,
        fda_brand_name:   fda_brand_name   || null,
        fda_generic_name: fda_generic_name || null,
        fda_labeler:      fda_labeler      || null,
        qty_received:     qty_received     || null,
        lot_number:       lot_number       || null,
        expiry:           expiry           || null,
        unit_cost:        unit_cost        || null,
        notes:            notes            || null,
        po_ref:           po_ref           || null,
        location_id:      location_id      || null,
        location_name:    location_name    || null,
        receiver_name:    receiver_name    || null,
        receiver_email:   receiver_email   || null,
        status:           'pending',
      })
      .select('id')
      .single()

    if (dbErr) throw new Error('DB insert failed: ' + dbErr.message)

    // 2. Send email via Resend
    const resendKey = Deno.env.get('RESEND_API_KEY')
    let emailSent = false
    let emailError: string | null = null

    if (resendKey) {
      const productDisplay = fda_brand_name || fda_generic_name || scanned_value || 'Unknown product'
      const locationDisplay = location_name ? `${location_name} (${location_id || '—'})` : (location_id || '—')

      const htmlBody = `
<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;color:#1C2B4A;">
  <div style="background:#1C2B4A;padding:18px 24px;border-radius:8px 8px 0 0;">
    <div style="color:#fff;font-size:16px;font-weight:700;">MedSync — Unknown Product Received</div>
    <div style="color:rgba(255,255,255,.6);font-size:12px;margin-top:2px;">Action required: product not found in MedSync</div>
  </div>
  <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 8px 8px;">

    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px;">
      <tr style="background:#F0EBF8;">
        <td colspan="2" style="padding:8px 12px;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#4A5568;">Product Information</td>
      </tr>
      <tr><td style="padding:7px 12px;color:#6B7280;width:40%;">Scanned barcode / NDC</td><td style="padding:7px 12px;font-family:monospace;">${scanned_value || '—'}</td></tr>
      ${fda_brand_name ? `<tr><td style="padding:7px 12px;color:#6B7280;">Brand name (FDA)</td><td style="padding:7px 12px;font-weight:600;">${fda_brand_name}</td></tr>` : ''}
      ${fda_generic_name ? `<tr><td style="padding:7px 12px;color:#6B7280;">Generic name (FDA)</td><td style="padding:7px 12px;">${fda_generic_name}</td></tr>` : ''}
      ${fda_labeler ? `<tr><td style="padding:7px 12px;color:#6B7280;">Manufacturer</td><td style="padding:7px 12px;">${fda_labeler}</td></tr>` : ''}
    </table>

    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px;">
      <tr style="background:#F0EBF8;">
        <td colspan="2" style="padding:8px 12px;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#4A5568;">Purchase Details</td>
      </tr>
      <tr><td style="padding:7px 12px;color:#6B7280;width:40%;">Quantity received</td><td style="padding:7px 12px;">${qty_received != null ? qty_received + ' units' : '—'}</td></tr>
      <tr><td style="padding:7px 12px;color:#6B7280;">Lot number</td><td style="padding:7px 12px;font-family:monospace;">${lot_number || '—'}</td></tr>
      <tr><td style="padding:7px 12px;color:#6B7280;">Expiration</td><td style="padding:7px 12px;">${expiry || '—'}</td></tr>
      <tr><td style="padding:7px 12px;color:#6B7280;">Unit cost</td><td style="padding:7px 12px;">${unit_cost != null ? '$' + Number(unit_cost).toFixed(4) : '—'}</td></tr>
      <tr><td style="padding:7px 12px;color:#6B7280;">PO / order reference</td><td style="padding:7px 12px;font-family:monospace;">${po_ref || '—'}</td></tr>
      ${notes ? `<tr><td style="padding:7px 12px;color:#6B7280;">Notes</td><td style="padding:7px 12px;">${notes}</td></tr>` : ''}
    </table>

    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:24px;">
      <tr style="background:#F0EBF8;">
        <td colspan="2" style="padding:8px 12px;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#4A5568;">Receiver</td>
      </tr>
      <tr><td style="padding:7px 12px;color:#6B7280;width:40%;">Name</td><td style="padding:7px 12px;">${receiver_name || '—'}</td></tr>
      <tr><td style="padding:7px 12px;color:#6B7280;">Email</td><td style="padding:7px 12px;">${receiver_email || '—'}</td></tr>
      <tr><td style="padding:7px 12px;color:#6B7280;">Location</td><td style="padding:7px 12px;">${locationDisplay}</td></tr>
    </table>

    <div style="background:#FFF8E1;border:1px solid #FDE68A;border-radius:8px;padding:14px 16px;font-size:12px;color:#92400E;">
      <strong>Next steps:</strong> Find or add this product in VetSpire, then enable it for ${location_name || 'the receiving location'}.
      The purchase record (ID: <code>${row.id}</code>) is saved in MedSync as <strong>pending</strong> and will sync automatically once the product is active.
    </div>
  </div>
</div>`

      try {
        const emailRes = await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${resendKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            from: FROM_EMAIL,
            to:   [ADMIN_EMAIL],
            subject: `[MedSync] Unknown product received — ${productDisplay} · ${locationDisplay}`,
            html: htmlBody,
          }),
        })

        const emailJson = await emailRes.json().catch(() => null)
        if (emailRes.ok) {
          emailSent = true
        } else {
          emailError = emailJson?.message || `Resend HTTP ${emailRes.status}`
        }
      } catch (e) {
        emailError = 'Email send failed: ' + String(e)
      }
    } else {
      emailError = 'RESEND_API_KEY not configured'
    }

    return new Response(JSON.stringify({
      ok: true,
      pending_receipt_id: row.id,
      email_sent: emailSent,
      email_error: emailError,
    }), { headers: CORS })

  } catch (err) {
    console.error('report-unknown-product error:', err)
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
      status: 500,
      headers: CORS,
    })
  }
})
