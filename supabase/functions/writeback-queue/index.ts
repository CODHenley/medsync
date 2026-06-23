import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type, authorization, apikey', 'Content-Type': 'application/json' }
const SUPA_URL = Deno.env.get('SUPABASE_URL')
const SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

async function getVetspireToken() {
  const token = Deno.env.get('VETSPIRE_API_TOKEN')
  if (!token) throw new Error('VETSPIRE_API_TOKEN secret not set')
  return token
}

async function getCurrentLevels(token, productId, locationId): Promise<{levels: Array<{stock: number, lotNumber: string|null, expirationDate: string|null}>, rawResponse: any}> {
  const r = await fetch('https://api.vetspire.com/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': token, 'Origin': 'https://scoutcare.vetspire.com' },
    body: JSON.stringify({
      query: 'query getStock($id: ID!, $locationId: ID!) { product(id: $id) { id inventoryLevels(locationId: $locationId) { stock lotNumber expirationDate } } }',
      variables: { id: String(productId), locationId: String(locationId) }
    })
  })
  const d = await r.json()
  const levels = d.data?.product?.inventoryLevels || []
  return {
    rawResponse: d,
    levels: levels.map((l: any) => ({ stock: parseFloat(l.stock || 0), lotNumber: l.lotNumber || null, expirationDate: l.expirationDate || null }))
  }
}

async function sendAdjustment(token, locationId, productId, quantityChange, lotNumber, expirationDate) {
  const result = await fetch('https://api.vetspire.com/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': token, 'Origin': 'https://scoutcare.vetspire.com' },
    body: JSON.stringify({
      query: 'mutation CreateInventoryAdjustment($input: InventoryAdjustmentInput!) { createInventoryAdjustment(input: $input) { id quantityChange } }',
      variables: { input: { locationId, productId, quantityChange, lotNumber: lotNumber || null, expirationDate: expirationDate || null, isWastage: false } }
    })
  })
  const resultJson = await result.json()
  if (resultJson.errors) throw new Error('Vetspire GQL error: ' + JSON.stringify(resultJson.errors))
  if (!resultJson.data?.createInventoryAdjustment) throw new Error('Vetspire adjustment returned null. Response: ' + JSON.stringify(resultJson))
  return resultJson.data.createInventoryAdjustment.id
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })
  try {
    const body = await req.json()
    const supabase = createClient(SUPA_URL, SERVICE_KEY)
    const token = await getVetspireToken()

    // Multi-lot clean-slate mode: body.lot_entries = [{quantity, lot_number, expiration_date}, ...]
    if (Array.isArray(body.lot_entries) && body.lot_entries.length > 0) {
      const totalQty = body.lot_entries.reduce((s: number, e: any) => s + parseFloat(e.quantity || 0), 0)
      const { levels: currentLevels, rawResponse: levelsRaw } = await getCurrentLevels(token, body.vetspire_product_id, body.vetspire_location_id)
      const currentStock = currentLevels.reduce((s, l) => s + l.stock, 0)

      // Log to queue
      const { data: row, error: insertErr } = await supabase
        .from('vetspire_writeback_queue')
        .insert({ vetspire_product_id: body.vetspire_product_id, vetspire_location_id: body.vetspire_location_id, quantity_change: totalQty - currentStock, lot_number: null, expiration_date: null, status: 'processing' })
        .select().single()
      if (insertErr) throw new Error('Insert failed: ' + JSON.stringify(insertErr))

      // Update snapshot
      const today = new Date().toISOString().slice(0,10)
      const { data: existing } = await supabase.from('inventory_snapshots').select('id').eq('vetspire_product_id', body.vetspire_product_id).eq('vetspire_location_id', body.vetspire_location_id).eq('snapshot_date', today).maybeSingle()
      if (existing) {
        await supabase.from('inventory_snapshots').update({ on_hand: totalQty }).eq('id', existing.id)
      } else {
        await supabase.from('inventory_snapshots').insert({ vetspire_product_id: body.vetspire_product_id, vetspire_location_id: body.vetspire_location_id, on_hand: totalQty, snapshot_date: today, product_name: body.product_name || '', location_name: body.location_name || '' })
      }

      const adjIds: string[] = []

      // Zero out each existing lot individually so no orphan quantities remain
      for (const level of currentLevels) {
        if (level.stock === 0) continue
        const zeroId = await sendAdjustment(token, body.vetspire_location_id, body.vetspire_product_id, -level.stock, level.lotNumber, level.expirationDate)
        adjIds.push('zero:' + zeroId)
      }

      // Add one adjustment per new lot entry
      for (const entry of body.lot_entries) {
        const qty = parseFloat(entry.quantity || 0)
        if (qty === 0) continue
        const adjId = await sendAdjustment(token, body.vetspire_location_id, body.vetspire_product_id, qty, entry.lot_number || null, entry.expiration_date || null)
        adjIds.push(adjId)
      }

      await supabase.from('vetspire_writeback_queue').update({ status: 'processed', processed_at: new Date().toISOString() }).eq('id', row.id)

      return new Response(JSON.stringify({ ok: true, adjustment_ids: adjIds, debug: { totalQty, currentStock, lotCount: body.lot_entries.length, zeroedLots: currentLevels.length, levelsRaw } }), { headers: CORS })
    }

    // Single-entry mode (existing behavior — differential adjustment)
    const actualCount = parseFloat(body.actual_count)
    const { levels: currentLevelsSingle } = await getCurrentLevels(token, body.vetspire_product_id, body.vetspire_location_id)
    const currentStock = currentLevelsSingle.reduce((s, l) => s + l.stock, 0)
    const quantityChange = actualCount - currentStock

    const { data: row, error: insertErr } = await supabase
      .from('vetspire_writeback_queue')
      .insert({ vetspire_product_id: body.vetspire_product_id, vetspire_location_id: body.vetspire_location_id, quantity_change: quantityChange, lot_number: body.lot_number || null, expiration_date: body.expiration_date || null, status: 'processing' })
      .select().single()
    if (insertErr) throw new Error('Insert failed: ' + JSON.stringify(insertErr))

    const today = new Date().toISOString().slice(0,10)
    const { data: existing } = await supabase.from('inventory_snapshots').select('id').eq('vetspire_product_id', body.vetspire_product_id).eq('vetspire_location_id', body.vetspire_location_id).eq('snapshot_date', today).maybeSingle()
    if (existing) {
      await supabase.from('inventory_snapshots').update({ on_hand: actualCount }).eq('id', existing.id)
    } else {
      await supabase.from('inventory_snapshots').insert({ vetspire_product_id: body.vetspire_product_id, vetspire_location_id: body.vetspire_location_id, on_hand: actualCount, snapshot_date: today, product_name: body.product_name || '', location_name: body.location_name || '' })
    }

    let adjId = null
    if (quantityChange !== 0 && !isNaN(quantityChange)) {
      adjId = await sendAdjustment(token, body.vetspire_location_id, body.vetspire_product_id, quantityChange, body.lot_number || null, body.expiration_date || null)
    }

    await supabase.from('vetspire_writeback_queue').update({ status: 'processed', processed_at: new Date().toISOString() }).eq('id', row.id)

    return new Response(JSON.stringify({ ok: true, adjustment_id: adjId, debug: { actual_count: actualCount, currentStock, quantityChange } }), { headers: CORS })
  } catch (e) {
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : String(e) }), { status: 400, headers: CORS })
  }
})
