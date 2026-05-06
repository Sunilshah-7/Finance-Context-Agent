# apps/worker-api

Cloudflare Worker API gateway.

## Build Responsibilities

- Auth/session validation.
- Portfolio CSV validation.
- R2 uploads.
- D1 metadata writes.
- Queue job creation.
- Secure calls to AMD Agent API.
- SSE streaming from AMD Agent API to browser.

## Suggested Stack

- TypeScript.
- Hono.
- Zod.
- Wrangler.

## Key Files

```text
src/
  index.ts
  routes/
    portfolio.ts
    jobs.ts
    analyze.ts
    chat.ts
  lib/
    auth.ts
    d1.ts
    r2.ts
    queues.ts
    amd-agent-client.ts
```

