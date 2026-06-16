# NVIDIA NIM Plan

`README.md` is the source of truth. NVIDIA NIM is the hosted chat-completions
backend behind the Go Inference Gateway.

## Current Contract

The Agent API must call the Inference Gateway, not NVIDIA NIM directly.

```text
Agent API
  -> INFERENCE_GATEWAY_URL
    -> POST /v1/chat/completions
      -> NIM_BASE_URL/chat/completions
```

Logical model mapping:

| Logical model | Environment variable | Default upstream |
|---------------|----------------------|------------------|
| `fincontext-planner` | `NIM_PLANNER_MODEL` | `Qwen/Qwen2.5-14B-Instruct` |
| `fincontext-reasoner` | `NIM_REASONER_MODEL` | `Qwen/Qwen2.5-72B-Instruct` |

Gateway config:

```text
NIM_API_KEY=
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_PLANNER_MODEL=Qwen/Qwen2.5-14B-Instruct
NIM_REASONER_MODEL=Qwen/Qwen2.5-72B-Instruct
```

## Implemented Today

- Go Gateway endpoint: `POST /v1/chat/completions`.
- Logical model name rewriting.
- Bearer-token forwarding to NIM.
- Gateway health reporting for NIM configuration.
- Lightweight request/error counters.

## Retrieval Models

Embeddings and reranking are not served by NIM in this repo. They stay behind
Gateway passthrough routes:

- `POST /v1/embeddings` -> `EMBEDDING_URL`
- `POST /v1/rerank` -> `RERANKER_URL`

These routes return `503` until their upstream URLs are configured.

## Why This Matters

The app depends on a stable Gateway contract. That lets the team change hosted
inference providers or model IDs without changing Agent API code or frontend
code.
