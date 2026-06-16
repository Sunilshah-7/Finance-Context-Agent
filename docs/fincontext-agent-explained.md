# FinContext Agent Explained

`README.md` is the source of truth. This is a plain-English explanation of the
current project.

## What It Does

FinContext Agent helps an investor or analyst understand how company disclosure
language changed over time and how those changes affect a portfolio. The demo
focuses on SEC filing evidence, disclosure drift, risk scores, and
citation-grounded memos.

## What Runs Today

The current app is a Go-first, fixture-backed prototype:

- The Agent API is a Go HTTP service.
- The Inference Gateway is a Go HTTP proxy.
- The demo UI is a Next.js analyst console exported as static assets.
- SQLite stores runs and seeded fixture metadata.
- Qdrant is initialized for the future `fincontext_chunks` collection.
- Curated JSON fixtures provide the current demo evidence and memo.

## Why Fixture Mode Exists

Fixture mode lets the team rehearse and show the product workflow before all
live ingestion/retrieval pieces are connected. It is not the target endpoint,
but it gives a stable user experience and validates the UI/API/citation shape.

## The Inference Gateway

The Gateway is the model boundary:

- `fincontext-planner` routes to the configured NIM planner model.
- `fincontext-reasoner` routes to the configured NIM reasoner model.
- `/v1/embeddings` routes to the configured embedding backend.
- `/v1/rerank` routes to the configured reranker backend.

The Agent API should depend on the Gateway contract, not provider-specific SDKs.

## Citation Discipline

Every fixture citation has an id. The app validates citation ids before returning
memo/chat output. When live retrieval is added, the same discipline should apply
to retrieved chunk ids and citation anchors.

## Current User Flow

1. The UI loads the fixture portfolio, diff, and metrics.
2. The user starts an analysis.
3. The Agent API advances a staged run.
4. The completed run returns fixture evidence, disclosure changes, risk scores,
   and memo.
5. The user can ask a chat question and receive validated citations.

## Target User Flow

1. EDGAR filings are ingested before the demo.
2. Filing sections are parsed and chunked.
3. Chunks are embedded and stored in Qdrant, with text/metadata in SQLite.
4. Analysis retrieves evidence with BM25 + vector search + reranking.
5. Disclosure changes are classified.
6. A memo is generated through the Gateway and citation-verified.

## Useful Local Commands

```bash
docker compose -f infra/docker-compose.yml --env-file .env up --build
curl http://localhost:8090/api/health
curl http://localhost:8080/health
```

Backend tests:

```bash
cd backend
GOCACHE=/absolute/path/to/.gocache GOMODCACHE=/absolute/path/to/.gomodcache go test ./...
```
