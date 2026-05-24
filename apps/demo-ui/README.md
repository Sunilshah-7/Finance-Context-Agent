---
title: FinContext Agent
colorFrom: slate
colorTo: blue
sdk: static
app_build_command: npm run build
app_file: dist/index.html
pinned: false
---

# FinContext Agent Demo UI

This directory contains the React/Vite demo console for FinContext Agent. It is
designed for HuggingFace Static Spaces and calls only the public Agent API.

The demo uses the polished analyst-console design from the local prototype while
still deploying through HuggingFace Spaces.

## What The UI Shows

| Tab | Purpose |
| --- | --- |
| Portfolio | Preview sample holdings and upload a CSV to Agent API |
| Analysis Run | Start an analysis job and refresh job status |
| Disclosure Drift | Compare old and current filing language with citation anchors |
| Evidence | Inspect citation-ready chunks returned by Agent API |
| Risk Scores | Show holding-level research risk movement |
| Analyst Memo | Render memo structure, watchlist questions, and disclaimer |
| AMD Benchmark | Show live metrics only when backend returns them |

## Backend Boundary

The browser app calls only Agent API. It does not call SQLite, Qdrant, the
Inference Gateway, vLLM, TEI, or EDGAR directly.

Static browser apps cannot keep secrets. Do not embed `AGENT_API_KEY` in this
frontend. Public demo authentication, CORS, and rate limiting must be handled by
the Agent API.

## Local Development

```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Build

```bash
npm run build
npm run preview
```

The static build is emitted to `dist/` and is the artifact served by
HuggingFace Static Spaces.

## Environment

For local development:

```bash
VITE_AGENT_API_URL=http://localhost:8090 npm run dev
```

For HuggingFace Static Spaces, configure:

```text
AGENT_API_URL=https://your-agent-api-url
```

The app also runs without Agent API. In that mode, it shows clearly labeled
sample data and unavailable benchmark placeholders.
