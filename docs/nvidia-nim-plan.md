# NVIDIA NIM Inference Plan

## What Changed

The original plan served Qwen models locally on large GPU instances. That is obsolete for the prototype: the $100 cloud budget is not enough to comfortably run and rehearse 70B-class inference. The current MVP uses NVIDIA NIM hosted chat-completions endpoints and keeps retrieval infrastructure local.

The application architecture did not change:

- Agent API still runs the LangGraph workflow.
- Ingestion and retrieval still use Qdrant and SQLite.
- All model-facing code still goes through the Inference Gateway.
- Citation verification and memo post-processing are unchanged.

Only the chat-completions upstream changed. The Agent API, LangGraph nodes, retrieval pipeline, citations, Qdrant, and SQLite contracts stay the same.

## Model Serving Architecture

```text
Agent API
  |
  v
Inference Gateway
  |
  +-- NVIDIA NIM hosted chat completions
  |     fincontext-reasoner -> Qwen2.5-72B-Instruct compatible endpoint
  |     fincontext-planner  -> Qwen2.5-14B-Instruct compatible endpoint
  |
  +-- Local TEI embeddings
  |     BAAI/bge-large-en-v1.5, 1024 dimensions
  |
  +-- Local TEI reranking
        BAAI/bge-reranker-large reranks reciprocal-rank-fused candidates
```

The Gateway should expose the same OpenAI-compatible surface to the rest of the app:

- `POST /v1/chat/completions`
- `POST /v1/embeddings`
- `POST /v1/rerank`
- `GET /health`
- `GET /metrics`

## Environment Variables

NVIDIA NIM is required for chat completions. Embeddings and reranking stay behind the Gateway so the Qdrant 1024-dimensional vector contract remains stable.

```bash
INFERENCE_GATEWAY_URL=http://localhost:8080

NIM_API_KEY=
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_REASONER_MODEL=Qwen/Qwen2.5-72B-Instruct
NIM_PLANNER_MODEL=Qwen/Qwen2.5-14B-Instruct

EMBEDDING_URL=http://localhost:8002
RERANKER_URL=http://localhost:8003
EMBEDDING_MODEL_ID=BAAI/bge-large-en-v1.5
RERANKER_MODEL_ID=BAAI/bge-reranker-large

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=fincontext_chunks
SQLITE_DB_PATH=./fincontext.db
```

Local 70B serving variables are intentionally not part of the prototype environment.

## Gateway Routing

| Logical model | Gateway model name | Upstream |
|---------------|--------------------|----------|
| Reasoner | `fincontext-reasoner` | NVIDIA NIM chat completions |
| Planner | `fincontext-planner` | NVIDIA NIM chat completions |
| Embeddings | `fincontext-embedding` | Local TEI BGE-large embedding service |
| Reranker | `fincontext-reranker` | Local TEI BGE reranker service |

The Agent API should never import a NIM, embedding, or reranker client directly. It calls the Gateway with logical model names and lets the Gateway translate those names to provider-specific routes.

## Metrics Plan

Run these scenarios and record metrics for the inference panel:

| Scenario | Description |
|----------|-------------|
| 1. Single 10-K analysis | AMD 2025 10-K, one question about risk factors |
| 2. Disclosure diff | AMD 2022 vs 2025 10-K, Item 1A comparison |
| 3. 5-stock portfolio review | Full demo portfolio, general portfolio review |
| 4. Interactive Q&A | Streaming chat over pre-analyzed portfolio |
| 5. Batch embedding | Embed 1,000 chunks, measure local embedding throughput |

Metrics to record for each:

```python
{
    "scenario": str,
    "provider": "nvidia-nim",
    "model": str,
    "input_tokens": int,
    "output_tokens": int,
    "time_to_first_token_ms": float,
    "total_latency_ms": float,
    "tokens_per_second": float,
    "concurrent_requests": int,
    "citation_pass_rate": float,
}
```

Save results to `packages/evals/benchmark_results.json`. The React inference metrics panel reads from this file.

## Operational Notes

- Keep `NIM_API_KEY` out of git and configure it as an environment variable or secret.
- Centralize retries, request IDs, timeout handling, and provider errors in the Gateway.
- Keep local embeddings deterministic for reproducible retrieval tests.
- Preserve the Gateway contract so inference providers can be swapped later without changing Agent API or ingestion code.
