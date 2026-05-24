# services/inference-gateway

Lightweight FastAPI proxy that sits between the Agent API and all model providers. In the current MVP, chat completions route to NVIDIA NIM hosted endpoints. Embeddings and reranking stay behind the same Gateway contract.

## Why this exists

- Agent API code is independent of which model is loaded or where it runs — swap models without touching agent code
- All model calls get request IDs, latency logging, and error normalization in one place
- The inference metrics panel gets its latency and token metrics from gateway logs
- Rate limiting and circuit-breaking can be added here without touching the Agent API

## Routing

| Request | Model field | Routes to | Port |
|---------|-------------|-----------|------|
| POST /v1/chat/completions | fincontext-reasoner | NVIDIA NIM reasoner | hosted |
| POST /v1/chat/completions | fincontext-planner | NVIDIA NIM planner | hosted |
| POST /v1/embeddings | fincontext-embedding | local BGE-large embedding service | 8002 |
| POST /v1/rerank | fincontext-reranker | local BGE reranker service | 8003 |
| GET /health | — | all services | — |
| GET /metrics | — | aggregated logs | — |

## Endpoints

```
POST /v1/chat/completions  — OpenAI-compatible, routed by model name
POST /v1/embeddings        — OpenAI-compatible, routes to embedding backend
POST /v1/rerank            — rerank format used by retrieval
GET  /health               — checks all 4 backend services
GET  /metrics              — returns recent request latency and token stats
```

## Stack

- Python 3.12
- FastAPI
- httpx (async proxy to backends)
- structlog (structured JSON logging for metrics collection)

## File Structure (target)

```
services/inference-gateway/
  main.py          # FastAPI app + route definitions
  router.py        # Routing logic based on model name
  middleware.py    # Request ID injection, latency measurement
  metrics.py       # In-memory metrics store (last N requests)
  models.py        # Pydantic request/response models
  requirements.txt
```

## Running

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Verify all backends are reachable
curl http://localhost:8080/health
```

## Metrics Output (for benchmark panel)

`GET /metrics` returns the last 1,000 requests aggregated by model:

```json
{
  "fincontext-reasoner": {
    "count": 12,
    "avg_input_tokens": 8420,
    "avg_output_tokens": 1850,
    "avg_time_to_first_token_ms": 380,
    "avg_total_latency_ms": 18240,
    "avg_tokens_per_second": 52.3
  },
  "fincontext-planner": {
    "count": 47,
    "avg_total_latency_ms": 2850,
    "avg_tokens_per_second": 112.1
  }
}
```

The Agent API metrics endpoint (`GET /api/benchmark/metrics`) fetches this and can add provider metadata such as upstream model name and NIM request status.

## Important: No Business Logic Here

This service is a transparent proxy. It must not modify request bodies, inject prompts, or alter model outputs. Its only jobs are routing, logging, and health checking.
