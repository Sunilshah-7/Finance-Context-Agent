# FinContext Agent

FinContext Agent is a production-oriented financial research application that turns filings and evidence into citation-grounded portfolio context. The backend is Go-first, with Python reserved for future offline parsing and evaluation workflows where its document/NLP ecosystem is useful.

The current implementation includes the production service boundaries now:

- **HuggingFace Space / web UI**: Next.js analyst console exported as static assets.
- **Agent API**: Go service for portfolio context, agent run orchestration, citation validation, SQLite persistence, Qdrant health/collection setup, and UI/API serving.
- **Inference Gateway**: Go service that exposes OpenAI-compatible model endpoints and routes logical FinContext model names to NVIDIA NIM.
- **Qdrant**: vector database service for production retrieval.
- **SQLite**: production metadata/run persistence for the Go Agent API.
- **NVIDIA NIM**: hosted LLM inference target behind the Gateway.

The app still ships curated JSON fixtures so the product can run deterministically before live EDGAR ingestion, embedding, and reranking are fully connected.

## Architecture

```tex
Browser / HuggingFace Space
  |
  v
Agent API (Go, :8090)
  ├─ serves exported Next.js UI
  ├─ orchestrates agent runs
  ├─ validates every citation id
  ├─ persists runs and seeded metadata in SQLite
  ├─ checks/initializes Qdrant collection
  └─ calls Inference Gateway for model work

Inference Gateway (Go, :8080)
  ├─ POST /v1/chat/completions -> NVIDIA NIM
  ├─ POST /v1/embeddings -> configured embedding backend
  ├─ POST /v1/rerank -> configured reranker backend
  ├─ GET /health
  └─ GET /metrics

Qdrant (:6333)
  └─ fincontext_chunks collection, 1024-dimensional cosine vectors

SQLite
  └─ agent_runs, portfolios, evidence_citations
```

## Services

### Agent API

Entrypoint: `backend/cmd/agent-api`

Endpoints:

- `GET /api/health`
- `GET /api/demo/portfolio`
- `POST /api/agent-runs`
- `GET /api/agent-runs/{run_id}`
- `GET /api/agent-runs/{run_id}/events`
- `GET /api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025`
- `POST /api/chat`
- `GET /api/metrics`

### Inference Gateway

Entrypoint: `backend/cmd/inference-gateway`

Endpoints:

- `GET /health`
- `GET /metrics`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`
- `POST /v1/rerank`

Logical chat model routing:

- `fincontext-planner` -> `NIM_PLANNER_MODEL`
- `fincontext-reasoner` -> `NIM_REASONER_MODEL`

## Local Production Stack

Create env config:

```bash
cp configs/.env.example .env
```

Start the production-shaped stack:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up --build
```

Then open:

```text
http://localhost:8090
```

Health checks:

```bash
curl http://localhost:8090/api/health
curl http://localhost:8080/health
curl http://localhost:6333/healthz
```

## HuggingFace Space

The root `Dockerfile` builds one public container for HuggingFace Spaces. It runs the Go Agent API and serves the exported Next.js UI. For a single-container Space, Qdrant/Gateway/NIM can be external services configured by env vars:

```text
PORT=7860
FIXTURE_DIR=/app/data/fixtures
STATIC_DIR=/app/public
SQLITE_DB_PATH=/tmp/fincontext.db
QDRANT_URL=https://your-qdrant-host
INFERENCE_GATEWAY_URL=https://your-gateway-host
NIM_API_KEY=...
```

For production, prefer separate long-running services for Agent API, Inference Gateway, Qdrant, and embedding/reranker backends.

## Development

Backend tests:

```bash
cd backend
GOCACHE=../.gocache GOMODCACHE=../.gomodcache go test ./...
```

Run Gateway:

```bash
cd backend
PORT=8080 NIM_API_KEY=... go run ./cmd/inference-gateway
```

Run Agent API:

```bash
cd backend
FIXTURE_DIR=../data/fixtures \
SQLITE_DB_PATH=../fincontext.db \
QDRANT_URL=http://localhost:6333 \
INFERENCE_GATEWAY_URL=http://localhost:8080 \
go run ./cmd/agent-api
```

Frontend only:

```bash
cd apps/demo-ui
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090 npm run dev
```

## Current Production Readiness

Implemented:

- Go Agent API service boundary
- Go Inference Gateway service boundary
- SQLite persistence for agent runs and seeded fixture metadata
- Qdrant health and collection initialization
- NIM-compatible chat proxy in the Gateway
- Embedding and reranker proxy routes in the Gateway
- Next.js analyst console
- Dockerfiles and Compose stack
- Citation fixture validation at startup

Still to build for full live production:

- EDGAR ingestion pipeline that writes chunks to SQLite and Qdrant
- Real embedding backend and reranker backend deployment
- Agent nodes that use retrieval results instead of curated fixtures
- Auth, rate limiting, tenant/user model, and production observability
- Public/private networking rules for Space -> Agent API -> Gateway/Qdrant

The fixture mode is now a bootstrap mode, not the target architecture.
