# apps/worker-api

**This service is NOT being built.**

The `apps/worker-api/` directory was part of a previous architecture plan that used a Cloudflare Worker as the API gateway between the frontend and the AMD Developer Cloud backend. That architecture was abandoned.

See `docs/architecture.md` for the full decision record.

## Why this was removed

The Cloudflare Worker API was planned to:
- Validate auth and payloads
- Upload files to Cloudflare R2
- Write metadata to Cloudflare D1
- Enqueue jobs to Cloudflare Queues
- Proxy requests to the AMD Agent API

All of this added 5 Cloudflare services to learn and configure during a 9-day hackathon, for no benefit beyond what the Agent API can do directly.

## What replaced it

The Gradio demo UI (in `apps/web/`) calls the Agent API (in `services/agent-api/`) directly over HTTPS. The Agent API handles:
- Portfolio CSV validation and SQLite storage
- Job creation and status tracking
- SSE streaming of analysis results
- Authentication via bearer token

The Cloudflare R2 document storage is replaced by local file storage on the AMD VM. The Cloudflare D1 database is replaced by SQLite. The Cloudflare Queues are replaced by FastAPI background tasks.

## Do not build anything in this directory.
