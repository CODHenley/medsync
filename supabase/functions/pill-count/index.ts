import Anthropic from 'npm:@anthropic-ai/sdk@0.30.0';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });

  try {
    const { image_base64, media_type = 'image/jpeg' } = await req.json();
    if (!image_base64) return new Response(JSON.stringify({ error: 'image_base64 required' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });

    const anthropic = new Anthropic({ apiKey: Deno.env.get('ANTHROPIC_API_KEY') });

    const message = await anthropic.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 256,
      messages: [{
        role: 'user',
        content: [
          {
            type: 'image',
            source: { type: 'base64', media_type: media_type as 'image/jpeg' | 'image/png' | 'image/gif' | 'image/webp', data: image_base64 },
          },
          {
            type: 'text',
            text: `Count the total number of individual pills, tablets, or capsules visible in this image.

Rules:
- Count every distinct pill, tablet, or capsule you can see
- If pills are partially hidden or stacked, estimate based on what is visible
- Do not count the counting tray, packaging, or anything that is not a pill
- Return ONLY a JSON object with no additional text:
{"count": <integer>, "confidence": "<high|medium|low>", "notes": "<one brief sentence if needed, else empty string>"}`,
          },
        ],
      }],
    });

    const raw = message.content[0].type === 'text' ? message.content[0].text.trim() : '';
    // Extract JSON from response (model may add whitespace/markdown)
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error('Model returned unexpected format: ' + raw.slice(0, 100));
    const result = JSON.parse(jsonMatch[0]);
    if (typeof result.count !== 'number') throw new Error('count must be a number');

    return new Response(JSON.stringify(result), {
      headers: { ...CORS, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('pill-count error:', err);
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
      status: 500,
      headers: { ...CORS, 'Content-Type': 'application/json' },
    });
  }
});
