# Cloudflare Deployment

## Deployment Role

Cloudflare should host the public app, edge API, storage coordination, job queues, and demo vector index. AMD Developer Cloud should host the GPU inference and agent services.

## Cloudflare Services

| Service | Use |
| --- | --- |
| Pages | Next.js frontend |
| Workers or Pages Functions | API gateway and authenticated endpoints |
| D1 | metadata database |
| R2 | document and report object storage |
| Queues | async ingestion and analysis jobs |
| Vectorize | demo vector store |
| KV | config cache, public model metadata |
| AI Gateway | observability, caching, provider routing for model requests |
| Turnstile | abuse protection on public demo |

## Target Routes

```text
/                         dashboard
/portfolio                holdings and exposure
/documents                filing explorer
/documents/:id            parsed document and citations
/diff/:ticker             latest vs prior filing changes
/memo/:jobId              generated analyst memo
/api/portfolio/upload     CSV upload
/api/jobs                 create/list jobs
/api/jobs/:id             job status
/api/analyze              start analysis
/api/chat                 citation-backed Q&A
```

## Worker Responsibilities

- Validate auth/session.
- Validate portfolio and prompt payloads.
- Store files in R2.
- Create D1 rows.
- Enqueue background jobs.
- Call AMD Agent API using service credentials.
- Stream model outputs to the browser.
- Redact secrets and signed URLs from client responses.

## D1 Setup

Create databases:

```bash
wrangler d1 create fincontext_prod
wrangler d1 create fincontext_preview
```

Apply migrations:

```bash
wrangler d1 migrations apply fincontext_prod
wrangler d1 migrations apply fincontext_preview
```

## R2 Setup

Create buckets:

```bash
wrangler r2 bucket create fincontext-documents
wrangler r2 bucket create fincontext-reports
```

Recommended object keys:

```text
portfolios/{user_id}/{portfolio_id}/upload.csv
filings/{ticker}/{filing_type}/{accession}/source.html
filings/{ticker}/{filing_type}/{accession}/parsed.md
filings/{ticker}/{filing_type}/{accession}/tables/{table_id}.json
reports/{portfolio_id}/{job_id}/memo.json
reports/{portfolio_id}/{job_id}/memo.md
```

## Queue Setup

Queues:

```bash
wrangler queues create fincontext-ingestion
wrangler queues create fincontext-analysis
```

Message types:

```json
{
  "type": "portfolio.analysis.requested",
  "portfolio_id": "p_123",
  "job_id": "job_123",
  "tickers": ["AMD", "MSFT"],
  "requested_by": "user_123"
}
```

## Vectorize Setup

For the demo, use one index:

```bash
wrangler vectorize create fincontext_chunks --dimensions=1024 --metric=cosine
```

If the chosen embedding dimension differs, change `--dimensions`.

Production note:

- Vectorize is excellent for a Cloudflare-native demo.
- For strict tenant isolation, larger corpora, and SQL joins, consider Postgres + pgvector or Qdrant behind the AMD Agent API.

## Secrets

Set these with `wrangler secret put`:

```text
AMD_AGENT_API_URL
AMD_AGENT_API_KEY
HF_TOKEN
SESSION_SECRET
SEC_USER_AGENT
```

Do not expose AMD GPU endpoints directly to the browser.

## Build and Deploy

Frontend:

```bash
cd apps/web
npm install
npm run build
wrangler pages deploy .vercel/output/static --project-name fincontext-agent
```

Worker API:

```bash
cd apps/worker-api
npm install
npm run deploy
```

Local dev:

```bash
wrangler pages dev apps/web/.vercel/output/static --compatibility-date=2026-05-06
```

## Networking to AMD Developer Cloud

Recommended:

- Put Agent API behind HTTPS.
- Require bearer token or mTLS.
- Allowlist Cloudflare egress where possible.
- Add request-level tenant IDs and job IDs.
- Use signed R2 URLs or short-lived object tokens for document transfer.

## Streaming

For interactive chat and memo generation:

- Browser connects to Cloudflare Worker.
- Worker calls AMD Agent API.
- Agent API streams SSE tokens.
- Worker forwards SSE stream.
- UI renders answer and citation cards incrementally.

## Deployment Checklist

- Cloudflare Pages project created.
- D1 databases created and migrations applied.
- R2 buckets created.
- Queues created and bound.
- Vectorize index created.
- Worker secrets configured.
- AMD Agent API reachable from Worker.
- CORS locked to the production domain.
- Rate limits enabled.
- Demo seed portfolio loaded.
- Source citation links verified.

