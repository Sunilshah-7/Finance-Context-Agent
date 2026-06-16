# Demo UI

This directory contains the Next.js analyst console for FinContext Agent. The
root Dockerfile builds it as static assets and the Go Agent API serves the
exported UI from `STATIC_DIR`.

`README.md` is the source of truth for the runnable architecture.

## Current Behavior

- Calls only the Agent API.
- Uses `NEXT_PUBLIC_API_BASE_URL` when running separately from the Agent API.
- Reads the fixture-backed demo portfolio, disclosure diff, metrics, chat answer,
  and agent run state from the Go backend.
- Polls `GET /api/agent-runs/{run_id}` for progress in the current UI.

The browser app never calls SQLite, Qdrant, the Inference Gateway, NVIDIA NIM,
embedding services, rerankers, or EDGAR directly.

## Local Development

```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090 npm run dev
```

## Build

```bash
npm run build
```

The current Next config exports static assets. In the HuggingFace container, the
root `Dockerfile` copies the export to `/app/public` and runs the Go Agent API.

## UI Sections

- Portfolio
- Agent run
- Disclosure diff
- Risk scores
- Analyst memo
- Chat and metrics
