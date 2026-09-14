export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return json({ error: 'POST required' }, 405);
    }

    const auth = request.headers.get('Authorization') || '';
    if (!env.PROXY_TOKEN || auth !== `Bearer ${env.PROXY_TOKEN}`) {
      return json({ error: 'Unauthorized' }, 401);
    }

    const upstreamKey = env.CHEAPAI_API_KEY;
    if (!upstreamKey) {
      return json({ error: 'CHEAPAI_API_KEY is not configured' }, 503);
    }

    const body = await request.text();
    const upstream = await fetch('https://cheapai.io/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${upstreamKey}`,
        'User-Agent': 'MamaHelperProxy/0.1',
      },
      body,
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') || 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
      },
    });
  },
};

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}
