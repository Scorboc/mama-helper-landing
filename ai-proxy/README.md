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

The backend is already prepared: when CHEAPAI_API_URL differs from the default CheapAI endpoint, it sends Authorization: Bearer CHEAPAI_PROXY_TOKEN to this proxy. The proxy then adds CHEAPAI_API_KEY only for the upstream CheapAI request.

Deploy:
```bash
npm install
npx wrangler login
npx wrangler secret put CHEAPAI_API_KEY
npx wrangler secret put PROXY_TOKEN
npm run deploy
```
