# Deployment

`README.md` is the source of truth. The current deployment is Go-first:
Agent API, Inference Gateway, Qdrant, and SQLite are run through Docker Compose
for a production-shaped local stack. The root `Dockerfile` builds the public
HuggingFace container with the Go Agent API serving the exported Next.js UI.

## Components

| Component | Where it runs | Technology |
|-----------|---------------|------------|
| Demo UI | Served by Agent API container | Next.js static export |
| Agent API | Container or local process | Go HTTP service |
| Inference Gateway | Container or local process | Go HTTP proxy |
| LLM inference | NVIDIA NIM | OpenAI-compatible chat completions |
| Embeddings | Configured external/backend service | Gateway passthrough |
| Reranker | Configured external/backend service | Gateway passthrough |
| Vector store | Container | Qdrant |
| Metadata DB | Local/container filesystem | SQLite |

## Local Production-Shaped Stack

```bash
cp configs/.env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up --build
```

Open:

```text
http://localhost:8090
```

Health checks:

```bash
curl http://localhost:8090/api/health
curl http://localhost:8080/health
curl http://localhost:6333/healthz
```

## Local Backend Development

Gateway:

```bash
cd backend
PORT=8080 NIM_API_KEY=... go run ./cmd/inference-gateway
```

Agent API:

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

## HuggingFace Space

The root `Dockerfile` is the HuggingFace container path. It:

1. Builds the Next.js UI.
2. Builds `backend/cmd/agent-api`.
3. Copies the static UI export to `/app/public`.
4. Runs the Go Agent API on `PORT=7860`.

For the single-container Space, configure external services with environment
variables:

```text
PORT=7860
FIXTURE_DIR=/app/data/fixtures
STATIC_DIR=/app/public
SQLITE_DB_PATH=/tmp/fincontext.db
QDRANT_URL=https://your-qdrant-host
INFERENCE_GATEWAY_URL=https://your-gateway-host
NIM_API_KEY=...
```

## Network Notes

- Only the Agent API needs to be public for the demo.
- Qdrant, Gateway, embedding, and reranker services should stay private when
  deployed as separate services.
- Static browser code cannot keep secrets, so do not embed private API keys in
  the UI.

## Current Limitations

- The public app runs on curated fixtures.
- Qdrant collection setup is implemented, but live vector retrieval is not yet
  connected to the Agent API run path.
- Embedding/reranker URLs are passthrough configuration, not bundled services.
