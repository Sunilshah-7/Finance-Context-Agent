# AGENTS.md

Master context file for coding agents working on this repository.

`README.md` is the source of truth for the current architecture, commands,
service boundaries, and readiness status.

## What We Are Building

FinContext Agent is a production-oriented financial research application for
the AMD Developer Hackathon 2026. It turns filings and evidence into
citation-grounded portfolio context, with disclosure-language drift as the hero
demo workflow.

The current implementation is Go-first:

- Agent API: Go service in `backend/cmd/agent-api`.
- Inference Gateway: Go service in `backend/cmd/inference-gateway`.
- Demo UI: Next.js analyst console in `apps/demo-ui`, exported and served by the
  Agent API.
- Qdrant: vector database service for production retrieval.
- SQLite: run and fixture metadata persistence for the Go Agent API.
- Fixtures: curated JSON data in `data/fixtures` powers the deterministic demo.

Python is reserved for future offline parsing and evaluation workflows where its
document/NLP ecosystem is useful. Do not recreate the old Python Agent API or
Python Gateway layout unless the team explicitly changes direction.

## What We Are Not Building

- A second frontend app.
- A second public Agent API.
- Local 70B GPU serving for the MVP.
- Broker integrations.
- Buy/sell/hold recommendations.
- Live ingestion during the judge demo.
- PDF parsing for MVP.

## Runtime Architecture

```text
Browser / HuggingFace Space
  |
  v
Agent API (Go, :8090)
  - serves exported Next.js UI
  - orchestrates fixture-backed agent runs
  - validates citation ids
  - persists runs and seeded fixture metadata in SQLite
  - checks/initializes Qdrant collection
  - checks Inference Gateway health

Inference Gateway (Go, :8080)
  - POST /v1/chat/completions -> NVIDIA NIM
  - POST /v1/embeddings -> configured embedding backend
  - POST /v1/rerank -> configured reranker backend
  - GET /health
  - GET /metrics

Qdrant (:6333)
  - fincontext_chunks collection, 1024-dimensional cosine vectors

SQLite
  - agent_runs, portfolios, evidence_citations
```

## Current Commands

Start the production-shaped stack:

```bash
cp configs/.env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up --build
```

Run backend tests:

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

Run frontend only:

```bash
cd apps/demo-ui
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090 npm run dev
```

## Implemented Endpoints

Agent API:

- `GET /api/health`
- `GET /api/demo/portfolio`
- `POST /api/agent-runs`
- `GET /api/agent-runs/{run_id}`
- `GET /api/agent-runs/{run_id}/events`
- `GET /api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025`
- `POST /api/chat`
- `GET /api/metrics`

Inference Gateway:

- `GET /health`
- `GET /metrics`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`
- `POST /v1/rerank`

## Model Boundary

All model-related calls go through the Inference Gateway.

- `fincontext-planner` maps to `NIM_PLANNER_MODEL`.
- `fincontext-reasoner` maps to `NIM_REASONER_MODEL`.
- `/v1/embeddings` maps to `EMBEDDING_URL` when configured.
- `/v1/rerank` maps to `RERANKER_URL` when configured.

Agent API code must not call NVIDIA NIM, embedding backends, or reranker
backends directly.

## Current Production Readiness

Implemented:

- Go Agent API service boundary.
- Go Inference Gateway service boundary.
- SQLite persistence for agent runs and seeded fixture metadata.
- Qdrant health and collection initialization.
- NIM-compatible chat proxy in the Gateway.
- Embedding and reranker proxy routes in the Gateway.
- Next.js analyst console.
- Dockerfiles and Compose stack.
- Citation fixture validation at startup.

Still to build:

- EDGAR ingestion pipeline that writes chunks to SQLite and Qdrant.
- Real embedding backend and reranker backend deployment.
- Agent nodes that use retrieval results instead of curated fixtures.
- Auth, rate limiting, tenant/user model, and production observability.
- Public/private networking rules for Space -> Agent API -> Gateway/Qdrant.

## Coding Conventions

- Follow existing Go patterns in `backend/internal`.
- Keep API response shapes aligned with `backend/internal/domain/types.go` and
  `docs/api-contracts.md`.
- Use structured logging; do not introduce ad hoc stdout logging in services.
- Keep citation validation in the request path for any generated memo/chat
  output.
- Keep the research-assistance disclaimer; never add investment advice.
- Do not commit `.env`, SQLite DB files, Qdrant volumes, model caches, or
  generated backups.

## Workload Division

Codex-owned areas:

- `backend/internal/gatewayapi`
- `backend/cmd/inference-gateway`
- `apps/demo-ui`
- `infra`
- ingestion/retrieval docs and future ingestion-worker implementation

Claude-owned areas:

- Agent API orchestration under `backend/internal/agent`
- API contracts and service behavior under `backend/internal/httpapi`
- shared Go domain contracts under `backend/internal/domain`

Coordinate before changing shared response/domain types.

## Git Workflow

- Branch from `dev`.
- Do not commit directly to `main` or `dev`.
- Open PRs targeting `dev`.
- Do not force-push shared branches.
- Commit messages should use:

```text
<type>(<scope>): <short description>
```

Examples:

```text
feat(agent-api): persist completed fixture runs
fix(gateway): normalize missing NIM key errors
docs(architecture): align service map with Go runtime
```
