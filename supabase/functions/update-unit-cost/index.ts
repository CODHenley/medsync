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

    if (!flag_id || !vetspire_product_id || new_unit_cost == null) {
      return new Response(JSON.stringify({ error: 'flag_id, vetspire_product_id, and new_unit_cost are required' }), { status: 400, headers: CORS })
    }

    const token = Deno.env.get('VETSPIRE_API_TOKEN')
    if (!token) throw new Error('VETSPIRE_API_TOKEN secret not set')

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    // Call VetSpire updateProduct mutation
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
          input: { unitCost: parseFloat(new_unit_cost) },
        },
      }),
    })

    const vsJson = await vsRes.json()

    if (vsJson.errors && vsJson.errors.length > 0) {
      throw new Error('VetSpire error: ' + JSON.stringify(vsJson.errors))
    }

    const updatedCost = vsJson.data?.updateProduct?.unitCost ?? new_unit_cost

    // Mark flag as synced
    const { error: patchErr } = await supabase
      .from('price_review_flags')
      .update({
        status: 'approved_synced',
        vetspire_synced: true,
        resolved_by: resolved_by || null,
        resolved_at: new Date().toISOString(),
      })
      .eq('id', flag_id)

    if (patchErr) throw new Error('Supabase patch failed: ' + patchErr.message)

    // Also update unit_cost in local products table if product_id is available
    const { data: flagRow } = await supabase
      .from('price_review_flags')
      .select('product_id')
      .eq('id', flag_id)
      .single()

    if (flagRow?.product_id) {
      await supabase
        .from('products')
        .update({ unit_cost: parseFloat(new_unit_cost) })
        .eq('id', flagRow.product_id)
    }

    return new Response(JSON.stringify({
      ok: true,
      vetspire_product_id,
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
