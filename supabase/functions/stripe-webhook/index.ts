import Stripe from 'https://esm.sh/stripe@14?target=deno';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2?target=deno';

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, { apiVersion: '2023-10-16' });

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
);

Deno.serve(async (req) => {
  const sig  = req.headers.get('stripe-signature');
  const body = await req.text();

  if (!sig) return new Response('Missing stripe-signature', { status: 400 });

  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      sig,
      Deno.env.get('STRIPE_WEBHOOK_SECRET')!,
    );
  } catch (e: any) {
    return new Response(`Webhook signature verification failed: ${e.message}`, { status: 400 });
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session;
    const { org_id, new_tier, new_limit } = session.metadata ?? {};

    if (org_id && new_tier) {
      const { error } = await supabase
        .from('organizations')
        .update({
          tier:           new_tier,
          location_limit: parseInt(new_limit ?? '999'),
        })
        .eq('id', org_id);

      if (error) {
        console.error('Failed to update org tier:', error.message);
        return new Response('DB update failed', { status: 500 });
      }
    }
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { 'Content-Type': 'application/json' },
  });
});
