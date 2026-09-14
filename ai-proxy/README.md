# Mama Helper AI Proxy

Cloudflare Worker proxy for CheapAI.

Why it exists:
- Poehali cloud functions currently time out on direct network calls to https://cheapai.io.
- The main backend can point to this worker through the server secret CHEAPAI_API_URL.
- CheapAI key stays outside the browser and outside GitHub.

Worker secrets:
- CHEAPAI_API_KEY: real CheapAI key.
- PROXY_TOKEN: random long token shared only with Poehali backend.

Poehali backend secrets after deploy:
- CHEAPAI_API_URL=https://your-worker.workers.dev
- CHEAPAI_PROXY_TOKEN=<same PROXY_TOKEN>

The current backend sends Authorization: Bearer CHEAPAI_API_KEY directly to CHEAPAI_API_URL.
If this proxy is used, update backend to send PROXY_TOKEN to the proxy and let the proxy add the CheapAI key upstream.
