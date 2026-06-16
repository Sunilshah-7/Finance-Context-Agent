# Architecture

`README.md` is the source of truth. This document expands the same current
architecture without reintroducing the earlier service plan.

## Current Decision

FinContext Agent is a Go-first, production-shaped prototype. The backend does
not run local 70B inference. Chat completions go through NVIDIA NIM behind a Go
Inference Gateway, while retrieval infrastructure, citation validation, Qdrant,
and SQLite remain auditable project components.

The app still uses curated JSON fixtures so the judge-facing product can run
deterministically before live EDGAR ingestion, embedding, reranking, and full
retrieval are connected.

## Runtime Topology

```text
Browser / HuggingFace Space
  |
  v
Agent API (Go, :8090)
  - serves exported Next.js UI
  - orchestrates fixture-backed agent runs
  - validates every citation id used by memo/chat fixtures
  - persists runs and seeded fixture metadata in SQLite
  - checks/initializes Qdrant collection
  - calls/checks Inference Gateway

Inference Gateway (Go, :8080)
  - POST /v1/chat/completions -> NVIDIA NIM
  - POST /v1/embeddings -> configured embedding backend
  - POST /v1/rerank -> configured reranker backend
  - GET /health
  - GET /metrics

Qdrant (:6333)
  - fincontext_chunks collection
  - 1024-dimensional cosine vectors

SQLite
  - agent_runs
  - portfolios
  - evidence_citations
```

## Implemented Service Responsibilities

### Agent API

Implementation: `backend/cmd/agent-api`

- Loads fixture data from `data/fixtures`.
- Seeds SQLite with the fixture portfolio and evidence citations.
- Creates staged agent runs and persists them.
- Returns curated evidence, disclosure changes, risk scores, memo, and metrics.
- Serves the exported Next.js UI when `STATIC_DIR` is configured.
- Reports dependency health for SQLite, Qdrant, and Gateway.

Current endpoints:

- `GET /api/health`
- `GET /api/demo/portfolio`
- `POST /api/agent-runs`
- `GET /api/agent-runs/{run_id}`
- `GET /api/agent-runs/{run_id}/events`
- `GET /api/diff`
- `POST /api/chat`
- `GET /api/metrics`

### Inference Gateway

Implementation: `backend/cmd/inference-gateway`

- Rewrites logical chat model names to configured NVIDIA NIM model IDs.
- Proxies chat completions to `NIM_BASE_URL`.
- Proxies embeddings to `EMBEDDING_URL` when configured.
- Proxies reranking to `RERANKER_URL` when configured.
- Exposes health and lightweight request/error metrics.

### Demo UI

Implementation: `apps/demo-ui`

- Next.js analyst console.
- Built as static assets by the root `Dockerfile`.
- Served by the Go Agent API in the HuggingFace container.
- Calls only Agent API endpoints.

### Qdrant

The current Agent API checks health and ensures the
`fincontext_chunks` collection exists with 1024-dimensional cosine vectors. Full
vector retrieval is future work.

### SQLite

The current schema is initialized by Go code and stores:

- agent run payloads
- seeded portfolio fixture JSON
- seeded evidence citation fixture JSON

The richer chunks/FTS schema described in older plans is target work for live
retrieval.

## Current Request Lifecycle

### Demo Load

```text
Browser requests /
  -> Agent API serves exported Next.js asset from STATIC_DIR
  -> UI calls /api/demo/portfolio, /api/diff, /api/metrics
  -> Agent API returns curated fixture data
```

### Agent Run

```text
UI POST /api/agent-runs
  -> Agent API creates run with queued stages
  -> background goroutine marks stages running/completed
  -> memo citations are validated against fixture evidence ids
  -> completed run contains evidence, disclosure changes, risk scores, memo
  -> SQLite stores serialized run payload
```

### Chat

```text
UI POST /api/chat
  -> fixture provider selects citation ids from the question
  -> citation validator verifies ids exist
  -> Agent API returns answer, citations, and research disclaimer
```

## Target Work

The target architecture remains compatible with the README but is not fully
implemented yet:

- EDGAR ingestion that writes chunk text and metadata to SQLite.
- Embedding generation through the Gateway.
- Qdrant vector upserts and search.
- Hybrid BM25 + vector retrieval with reranking.
- Agent nodes that use retrieved chunks instead of curated fixtures.
- Auth, rate limiting, tenancy, and production observability.
