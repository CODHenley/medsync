import Stripe from 'https://esm.sh/stripe@14?target=deno';

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, { apiVersion: '2023-10-16' });

const TIER_LIMITS: Record<string, number> = {
  small_group: 3,
  mid_group:   6,
  large_group: 12,
  enterprise:  999,
};

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });

  try {
    const { org_id, new_tier, price_id, success_url, cancel_url } = await req.json();

    if (!org_id || !new_tier || !price_id) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), { status: 400, headers: CORS });
    }

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      line_items: [{ price: price_id, quantity: 1 }],
      success_url: success_url ?? 'https://medsync.vet/medsync_newlocation_live.html?upgraded=1',
      cancel_url:  cancel_url  ?? 'https://medsync.vet/medsync_newlocation_live.html',
      metadata: {
        org_id,
        new_tier,
        new_limit: String(TIER_LIMITS[new_tier] ?? 999),
      },
    });

    return new Response(JSON.stringify({ url: session.url }), {
      headers: { ...CORS, 'Content-Type': 'application/json' },
    });
  } catch (e: any) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { ...CORS, 'Content-Type': 'application/json' },
    });
  }
});
