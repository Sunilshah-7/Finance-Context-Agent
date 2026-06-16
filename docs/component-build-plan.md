# Component Build Plan

`README.md` is the source of truth. This plan reflects the current Go-first
implementation and the remaining work to move from fixture mode to live
retrieval.

## Implemented Components

### Agent API

Location:

- `backend/cmd/agent-api`
- `backend/internal/httpapi`
- `backend/internal/agent`
- `backend/internal/citations`
- `backend/internal/sqlstore`
- `backend/internal/vector`

Status:

- Serves exported UI assets.
- Serves fixture-backed API endpoints.
- Persists runs in SQLite.
- Seeds fixture portfolio/evidence citation metadata.
- Validates fixture memo/chat citations.
- Checks Qdrant and Gateway health.
- Ensures the Qdrant collection exists.

### Inference Gateway

Location:

- `backend/cmd/inference-gateway`
- `backend/internal/gatewayapi`

Status:

- Proxies chat completions to NVIDIA NIM.
- Rewrites logical model names.
- Proxies embeddings/rerank to configured upstreams.
- Provides health and lightweight metrics.

### Demo UI

Location:

- `apps/demo-ui`

Status:

- Next.js analyst console.
- Calls only Agent API.
- Renders portfolio, run progress, disclosure diff, risk scores, memo, chat, and
  metrics from current API responses.

### Deployment

Location:

- `Dockerfile`
- `Dockerfile.agent-api`
- `Dockerfile.inference-gateway`
- `infra/docker-compose.yml`
- `configs/.env.example`

Status:

- Compose stack runs Qdrant, Gateway, and Agent API.
- Root Dockerfile builds one HuggingFace-ready container with exported UI and
  Agent API.

## Remaining Build Work

1. EDGAR ingestion pipeline that writes parsed chunks to SQLite and Qdrant.
2. Embedding backend deployment and Gateway configuration.
3. Reranker backend deployment and Gateway configuration.
4. Retrieval service code: BM25, Qdrant vector search, RRF, rerank, diversity.
5. Agent API run path that uses retrieved evidence instead of curated fixtures.
6. Auth/rate limiting/tenant model for public deployment.
7. Production observability beyond fixture metrics.

## Validation Commands

Backend:

```bash
cd backend
GOCACHE=/absolute/path/to/.gocache GOMODCACHE=/absolute/path/to/.gomodcache go test ./...
```

Stack:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up --build
curl http://localhost:8090/api/health
curl http://localhost:8080/health
curl http://localhost:6333/healthz
```
