import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

const FROM_EMAIL = 'medsync@medsync.vet'

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const { recipient_id, sender_name, preview, dm_channel } = await req.json()

    if (!recipient_id || !sender_name) {
      return new Response(JSON.stringify({ error: 'recipient_id and sender_name are required' }), { status: 400, headers: CORS })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    // Look up recipient email from auth.users via service role
    const { data: authUser, error: authErr } = await supabase.auth.admin.getUserById(recipient_id)
    if (authErr || !authUser?.user?.email) {
      return new Response(JSON.stringify({ error: 'Recipient not found', detail: authErr?.message }), { status: 404, headers: CORS })
    }

    const recipientEmail = authUser.user.email

    // Look up recipient name
    const { data: userRow } = await supabase
      .from('users')
      .select('full_name')
      .eq('id', recipient_id)
      .single()
    const recipientName = userRow?.full_name?.split(' ')[0] || 'there'

    const resendKey = Deno.env.get('RESEND_API_KEY')
    if (!resendKey) {
      return new Response(JSON.stringify({ error: 'RESEND_API_KEY not configured' }), { status: 500, headers: CORS })
    }

    const previewText = preview ? `"${preview.slice(0, 100)}${preview.length > 100 ? '…' : ''}"` : 'You have a new message.'

    // Build deep-link URL — for DM threads, append ?open_dm=CHANNEL so the page
    // opens directly into that conversation. For staff @mentions, link to staff channel.
    const baseUrl = 'https://medsync.vet/medsync_portfolio_live.html'
    const deepLink = dm_channel && dm_channel.includes(':')
      ? `${baseUrl}?open_dm=${encodeURIComponent(dm_channel)}`
      : baseUrl

    const isDM = dm_channel && dm_channel.includes(':')
    const contextLabel = isDM ? 'sent you a direct message' : 'mentioned you in the Staff Channel'
    const btnLabel = isDM ? 'Open Direct Message →' : 'Open Staff Channel →'

    const html = `
      <div style="font-family:'DM Sans',Arial,sans-serif;max-width:480px;margin:0 auto;background:#fff;border-radius:12px;border:1px solid #EDE8F8;overflow:hidden;">
        <div style="background:#1C2B4A;padding:20px 24px;display:flex;align-items:center;gap:12px;">
          <span style="font-size:24px;font-weight:700;color:#fff;letter-spacing:-1px;">Med<span style="color:#C8922A;">Sync</span></span>
        </div>
        <div style="padding:24px;">
          <p style="margin:0 0 8px;font-size:15px;font-weight:600;color:#1C2B4A;">Hi ${recipientName},</p>
          <p style="margin:0 0 16px;font-size:14px;color:#4A5568;"><strong>${sender_name}</strong> ${contextLabel}:</p>
          <div style="background:#F7F5FF;border-left:3px solid #9B8EC4;border-radius:6px;padding:12px 16px;margin-bottom:20px;">
            <p style="margin:0;font-size:14px;color:#1C2B4A;font-style:italic;">${previewText}</p>
          </div>
          <a href="${deepLink}" style="display:inline-block;background:#1C2B4A;color:#fff;text-decoration:none;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;">${btnLabel}</a>
        </div>
        <div style="padding:12px 24px;background:#F9F7FF;border-top:1px solid #EDE8F8;">
          <p style="margin:0;font-size:11px;color:#9B8EC4;">You're receiving this because you have an unread message in MedSync. Log in to reply.</p>
        </div>
      </div>
    `

    const emailRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${resendKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: `MedSync <${FROM_EMAIL}>`,
        to: [recipientEmail],
        subject: `💬 New message from ${sender_name} on MedSync`,
        html,
      }),
    })

    const emailData = await emailRes.json()
    if (!emailRes.ok) {
      return new Response(JSON.stringify({ error: 'Email send failed', detail: emailData }), { status: 502, headers: CORS })
    }

    return new Response(JSON.stringify({ ok: true, email_id: emailData.id }), { headers: CORS })

  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), { status: 500, headers: CORS })
  }
})
