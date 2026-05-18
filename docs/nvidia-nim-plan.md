# NVIDIA NIM Inference Plan

## What Changed

The original plan served Qwen and BGE models with a local model-serving stack. The current MVP uses NVIDIA NIM hosted inference for LLM calls and keeps retrieval infrastructure local.

The application architecture did not change:

- Agent API still runs the LangGraph workflow.
- Ingestion and retrieval still use Qdrant and SQLite.
- All model-facing code still goes through the Inference Gateway.
- Citation verification and memo post-processing are unchanged.

Only the Gateway's upstream inference provider changed.

## Model Serving Architecture

```text
Agent API
  |
  v
Inference Gateway
  |
  +-- NVIDIA NIM hosted chat completions
  |     fincontext-reasoner -> Qwen2.5-72B-Instruct compatible endpoint
  |     fincontext-planner  -> Qwen2.5-7B-Instruct compatible endpoint
  |
  +-- Local embeddings
  |     used for ingestion and query embeddings
  |
  +-- Reranking
        reciprocal-rank-fused candidates are reranked before diversity filtering
```

The Gateway should expose the same OpenAI-compatible surface to the rest of the app:

- `POST /v1/chat/completions`
- `POST /v1/embeddings`
- `POST /v1/rerank`
- `GET /health`
- `GET /metrics`

## Environment Variables

Use provider-neutral names for new configuration where possible:

```bash
INFERENCE_GATEWAY_URL=http://localhost:8080

NIM_API_KEY=
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_REASONER_MODEL=Qwen/Qwen2.5-72B-Instruct
NIM_PLANNER_MODEL=Qwen/Qwen2.5-7B-Instruct

EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_ID=sentence-transformers/all-MiniLM-L6-v2
RERANKER_PROVIDER=local

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=fincontext_chunks
SQLITE_DB_PATH=./fincontext.db
```

Legacy local-serving variables may remain in older local-development scripts, but documentation and new code should describe the live architecture as NIM-backed.

## Gateway Routing

| Logical model | Gateway model name | Upstream |
|---------------|--------------------|----------|
| Reasoner | `fincontext-reasoner` | NVIDIA NIM chat completions |
| Planner | `fincontext-planner` | NVIDIA NIM chat completions |
| Embeddings | `fincontext-embedding` | Local embedding service |
| Reranker | `fincontext-reranker` | Local reranker or scoring implementation |

The Agent API should never import a NIM client directly. It calls the Gateway with logical model names and lets the Gateway translate those names to provider-specific model IDs.

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

Save results to `packages/evals/benchmark_results.json`. The Gradio inference metrics panel reads from this file.

## Operational Notes

- Keep `NIM_API_KEY` out of git and configure it as an environment variable or secret.
- Centralize retries, request IDs, timeout handling, and provider errors in the Gateway.
- Keep local embeddings deterministic for reproducible retrieval tests.
- Preserve the Gateway contract so local GPU serving can be reintroduced later without changing Agent API or ingestion code.
