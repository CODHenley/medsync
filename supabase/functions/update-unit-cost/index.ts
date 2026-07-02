import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const { flag_id, vetspire_product_id, new_unit_cost, resolved_by } = await req.json()

    if (!flag_id || new_unit_cost == null) {
      return new Response(JSON.stringify({ error: 'flag_id and new_unit_cost are required' }), { status: 400, headers: CORS })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    let updatedCost = parseFloat(new_unit_cost)
    let vetspireSynced = false

    // Call VetSpire only when we have a product ID
    if (vetspire_product_id) {
      const token = Deno.env.get('Medsync_API_Key')
      if (!token) throw new Error('Medsync_API_Key secret not set')

      const vsRes = await fetch('https://api.vetspire.com/graphql', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token,
          'Origin': 'https://scoutcare.vetspire.com',
        },
        body: JSON.stringify({
          query: `mutation UpdateProductCost($id: ID!, $input: UpdateProductInput!) {
            updateProduct(id: $id, input: $input) {
              id
              unitCost
            }
          }`,
          variables: {
            id: String(vetspire_product_id),
            input: { unitCost: updatedCost },
          },
        }),
      })

      const vsJson = await vsRes.json()
      if (vsJson.errors && vsJson.errors.length > 0) {
        throw new Error('VetSpire error: ' + JSON.stringify(vsJson.errors))
      }
      updatedCost = vsJson.data?.updateProduct?.unitCost ?? updatedCost
      vetspireSynced = true
    }

    // Mark flag resolved in Supabase
    const { error: patchErr } = await supabase
      .from('price_review_flags')
      .update({
        status: vetspireSynced ? 'approved_synced' : 'approved_pending_sync',
        vetspire_synced: vetspireSynced,
        resolved_by: resolved_by || null,
        resolved_at: new Date().toISOString(),
      })
      .eq('id', flag_id)

    if (patchErr) throw new Error('Supabase patch failed: ' + patchErr.message)

    // Also update unit_price in local products table if product_id is available
    const { data: flagRow } = await supabase
      .from('price_review_flags')
      .select('product_id')
      .eq('id', flag_id)
      .single()

    if (flagRow?.product_id) {
      await supabase
        .from('products')
        .update({ unit_price: updatedCost })
        .eq('id', flagRow.product_id)
    }

    return new Response(JSON.stringify({
      ok: true,
      vetspire_product_id: vetspire_product_id || null,
      vetspire_synced: vetspireSynced,
      new_unit_cost: updatedCost,
      flag_id,
    }), { headers: CORS })

  } catch (err) {
    console.error('update-unit-cost error:', err)
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
      status: 500,
      headers: CORS,
    })
  }
})
