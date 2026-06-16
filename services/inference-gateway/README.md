# Inference Gateway

This service is implemented in Go under `backend/cmd/inference-gateway`. The
Gateway exposes OpenAI-compatible endpoints and routes logical FinContext model
names to NVIDIA NIM or configured retrieval-model backends.

`README.md` is the source of truth for the runnable architecture.

## Current Responsibilities

- `POST /v1/chat/completions` proxies to NVIDIA NIM.
- `fincontext-planner` is rewritten to `NIM_PLANNER_MODEL`.
- `fincontext-reasoner` is rewritten to `NIM_REASONER_MODEL`.
- `POST /v1/embeddings` proxies to `EMBEDDING_URL` when configured.
- `POST /v1/rerank` proxies to `RERANKER_URL` when configured.
- `GET /health` reports configured upstream status.
- `GET /metrics` returns simple request/error counters.

The Gateway does not inject prompts or business logic. It only routes,
normalizes errors, and records lightweight metrics.

## Local Run

```bash
cd backend
PORT=8080 NIM_API_KEY=... go run ./cmd/inference-gateway
```

Health check:

```bash
curl http://localhost:8080/health
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Gateway listen port |
| `NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM OpenAI-compatible base URL |
| `NIM_API_KEY` | empty | Required for chat completions |
| `NIM_PLANNER_MODEL` | `Qwen/Qwen2.5-14B-Instruct` | Upstream planner model |
| `NIM_REASONER_MODEL` | `Qwen/Qwen2.5-72B-Instruct` | Upstream reasoner model |
| `EMBEDDING_URL` | empty | Optional embedding backend base URL |
| `RERANKER_URL` | empty | Optional reranker backend base URL |
| `UPSTREAM_TIMEOUT_SECONDS` | `60` | Gateway upstream timeout |

## Routes

| Endpoint | Current behavior |
|----------|------------------|
| `GET /health` | Reports NIM, embedding, reranker configuration |
| `GET /metrics` | Returns request/error counters |
| `POST /v1/chat/completions` | Rewrites logical model names and proxies to NIM |
| `POST /v1/embeddings` | Proxies to configured embedding backend |
| `POST /v1/rerank` | Proxies to configured reranker backend |
