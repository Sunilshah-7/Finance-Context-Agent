# services/inference-gateway

Internal gateway for model calls running near AMD GPU inference services.

## Build Responsibilities

- Route chat completion calls to vLLM.
- Route embedding calls to embedding model service.
- Route reranking calls to reranker service.
- Enforce internal auth.
- Record latency and token metrics.
- Normalize OpenAI-compatible responses.

## Key Endpoints

```text
POST /v1/chat/completions
POST /v1/embeddings
POST /v1/rerank
GET /health
GET /metrics
```

