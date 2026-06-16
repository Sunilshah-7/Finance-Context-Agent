# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.
`README.md` is the source of truth for current architecture and commands.

## Project

FinContext Agent is an AMD Developer Hackathon 2026 Track 1 project. It turns
filings and curated evidence into citation-grounded portfolio context, with a
hero workflow around disclosure-language drift.

## Current Architecture Decision

The current implementation is Go-first. Python is reserved for future offline
parsing/evaluation workflows where its document/NLP ecosystem is useful.

```text
Agent API           port 8090  Go HTTP service
Inference Gateway   port 8080  Go proxy to NVIDIA NIM + retrieval backends
Qdrant              port 6333  Vector store
SQLite              on disk    Run and fixture metadata
Demo UI             served by Agent API as exported Next.js static assets
```

The app currently runs in fixture mode: curated JSON data powers the demo while
live EDGAR ingestion, retrieval, embeddings, reranking, and live memo generation
are connected incrementally.

## Commands

Production-shaped local stack:

```bash
cp configs/.env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up --build
```

Backend tests:

```bash
cd backend
GOCACHE=/absolute/path/to/.gocache GOMODCACHE=/absolute/path/to/.gomodcache go test ./...
```

Run Gateway locally:

```bash
cd backend
PORT=8080 NIM_API_KEY=... go run ./cmd/inference-gateway
```

Run Agent API locally:

```bash
cd backend
FIXTURE_DIR=../data/fixtures \
SQLITE_DB_PATH=../fincontext.db \
QDRANT_URL=http://localhost:6333 \
INFERENCE_GATEWAY_URL=http://localhost:8080 \
go run ./cmd/agent-api
```

Run demo UI separately:

```bash
cd apps/demo-ui
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090 npm run dev
```

## Model Boundary

All model-related calls go through the Inference Gateway:

| Task | Gateway route/model | Backend |
|------|---------------------|---------|
| Planner calls | `fincontext-planner` | NVIDIA NIM planner model |
| Final memo calls | `fincontext-reasoner` | NVIDIA NIM reasoner model |
| Embeddings | `POST /v1/embeddings` | configured embedding backend |
| Reranking | `POST /v1/rerank` | configured reranker backend |

Do not call NVIDIA NIM, embedding services, or reranker services directly from
Agent API code.

## Compliance Rules

- Every factual memo/chat claim should be traceable to a known citation.
- Never generate buy, sell, hold, short, or other investment recommendations.
- Every memo/chat answer must include the research-assistance disclaimer.
- Do not add a second public Agent API or frontend app without a team decision.
