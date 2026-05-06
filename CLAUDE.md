# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FinContext Agent — AMD Developer Hackathon 2026 submission (Track 1: AI Agents & Agentic Workflows). A portfolio-aware financial intelligence platform that ingests SEC filings from EDGAR, detects material disclosure changes year-over-year, scores risk per portfolio holding, and produces citation-grounded analyst memos. The entire compute and storage stack runs on one AMD Developer Cloud VM; the public demo UI lives on HuggingFace Spaces.

**Hackathon constraint: 9-day build phase May 11–19, 2026. Three developers. $100 AMD Developer Cloud credit.**

All planning docs are in `docs/`. No application code exists yet — the build phase ends May 11.

## Critical Architecture Decision

An earlier version of this plan (see branch `codex-plan-branch`) used Cloudflare Pages, Workers, D1, R2, Vectorize, and Queues as the app/edge layer. That architecture was **deliberately abandoned** because:

- Cloudflare Workers have a 128 MB memory limit and 50 ms CPU-time limit per request — incompatible with any real ML workload
- Learning 9 unfamiliar Cloudflare services under a 9-day deadline is a schedule risk that cannot be absorbed
- Cloudflare Vectorize has limited payload filtering compared to Qdrant
- The AMD Developer Cloud VM can run the API, store files, and run Qdrant in Docker at zero extra cost
- All inter-service communication becomes localhost calls instead of cross-cloud HTTPS hops

**Do not reintroduce Cloudflare dependencies.** The `apps/worker-api/` and `apps/web/` directories in the repo are stubs from the old plan and are not being built. The new frontend is Gradio in `apps/demo-ui/`.

## Deployment Architecture

```
AMD Developer Cloud VM  (everything runs here)
├── Inference Gateway   port 8080  — FastAPI proxy to all model services
├── Agent API           port 8090  — FastAPI + LangGraph, 4-node agent graph
├── vLLM reasoner       port 8000  — Qwen2.5-72B-Instruct, FP16, ROCm
├── vLLM planner        port 8001  — Qwen2.5-14B-Instruct, FP16, ROCm
├── Embedding service   port 8002  — BAAI/bge-large-en-v1.5 via TEI or vLLM
├── Reranker service    port 8003  — BAAI/bge-reranker-large via TEI
├── Qdrant              port 6333  — Vector store, Docker, persistent volume
└── SQLite              on-disk    — Metadata: portfolios, holdings, jobs, findings, chunks

HuggingFace Spaces  (public demo, free tier)
└── Gradio app  →  calls Agent API at AMD_VM_PUBLIC_IP:8090 over HTTPS
```

The Inference Gateway is the only external-facing model endpoint. Agent API calls Gateway. Gradio calls Agent API. No service bypasses the Gateway for model calls.

## Repository Layout (target — no code written yet)

```

services/
      agent-api/          # FastAPI + LangGraph 4-node agent graph
      ingestion-worker/   # SEC EDGAR fetch, parse, chunk, embed → Qdrant + SQLite
      inference-gateway/  # FastAPI proxy to vLLM, embedding, reranker
apps/
      demo-ui/            # Gradio app — deployed to HuggingFace Spaces
packages/
      schemas/            # Shared Pydantic models (Python) + generated TS types
      evals/              # Retrieval recall, citation precision, latency benchmarks
infra/
      amd-gpu/            # Docker Compose: vLLM 72B, vLLM 14B, embedding, reranker, Qdrant
      schema.sql          # SQLite schema
configs/
      .env.example
docs/
```

## Commands

**Start all GPU and storage services (AMD VM only):**
```bash
cd infra/amd-gpu
cp configs/.env.example .env       # fill HF_TOKEN, model vars
docker compose up -d                      # starts all model services + Qdrant
docker compose logs -f vllm-72b          # watch 72B model load (~3-5 min)
curl http://localhost:8000/health         # verify vLLM ready
curl http://localhost:6333/healthz        # verify Qdrant ready
```

**One-time: create SQLite schema:**
```bash
sqlite3 fincontext.db < infra/schema.sql
```

**Pre-ingest all demo data (do this before build phase demo):**
```bash
cd services/ingestion-worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python ingest.py --tickers AMD,NVDA,MSFT,JPM,TSLA \
                 --filing-types 10-K,10-Q \
                 --years 4 \
                 --db-path ../../fincontext.db \
                 --qdrant-url http://localhost:6333
```

**Run agent API (development):**
```bash
cd services/agent-api
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

**Run agent API tests:**
```bash
pytest tests/ -x                                          # all tests, stop on first fail
pytest tests/test_graph.py -x                             # agent graph tests
pytest tests/test_retrieval.py::test_hybrid_merge -x      # single test
```

**Run Gradio demo locally:**
```bash
cd apps/demo-ui
pip install -r requirements.txt
AGENT_API_URL=http://localhost:8090 python app.py          # http://localhost:7860
```

**Deploy Gradio to HuggingFace Spaces:**
```bash
huggingface-cli login
# push only the demo-ui subdirectory as the Space root
git subtree push --prefix /apps/demo-ui space main
```

## LangGraph Agent Graph (4 nodes)

Graph defined in `services/agent-api/app/graph.py`. Fixed linear routing:

```
portfolio_context_planner
        ↓
  filing_retrieval
        ↓
  disclosure_change
        ↓
   analyst_memo
```

Shared state type: `AnalysisState` in `packages/schemas/python/state.py`. Nodes only read and mutate state — they never call other nodes directly. LangGraph handles routing and retries.

Rules:
- Never add a node without updating `AnalysisState` and writing a node-isolation test first
- Nodes must use structured Pydantic output, never freeform text, except the final memo node
- If a node cannot produce a valid result, it sets an error field in state and the graph short-circuits to return a partial response — never raise an unhandled exception

## Citation Anchors (hard invariant)

Every chunk stored in Qdrant must have a `citation_anchor` string in this exact format:
```
{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}
```
Example: `AMD 10-K Item 1A paragraph 42`

The memo node runs a post-processing pass: every `[citation_id]` in generated text must map to a chunk ID in the state's `retrieved_chunks`. Sentences with unmapped citations are removed before returning. Never silently keep an unsupported claim.

## Retrieval Pipeline

```
user query
  → BM25 keyword search  (SQLite FTS5 on chunks table)
  + vector search         (Qdrant HNSW, cosine similarity)
  → reciprocal rank fusion (k=60)
  → BGE cross-encoder reranker (AMD GPU, port 8003)
  → section diversity filter (max 3 chunks per section per ticker)
  → top 12 citation-ready chunks returned to agent graph
```

Build and test retrieval as a standalone deterministic service before wiring it into the agent graph. Given the same query and metadata filters, retrieval must return the same ranked list (no randomness in retrieval).

Required Qdrant payload filters on every query: `ticker` (eq), `filing_type` (in), `filed_at` (range).

## Pre-Ingestion Strategy

**Never demo live ingestion in front of judges.** Pre-ingest all data before May 10.

Demo corpus:
- Tickers: AMD, NVDA, MSFT, JPM, TSLA
- Filing types: 10-K for 2022, 2023, 2024, 2025 where available; latest 2 10-Q per company
- Source: SEC EDGAR HTML only — no PDF parsing for MVP (EDGAR HTML has item labels that make section detection reliable)
- Estimated volume: ~50 documents, ~12,000–18,000 chunks

After ingestion completes, snapshot the Qdrant collection and SQLite DB. Both teammates must be able to load this snapshot and reproduce the demo state without re-running ingestion.

## Model Allocation (protect the $100 credit)

| Task | Model | Port | Rationale |
|------|-------|------|-----------|
| Retrieval planning | Qwen2.5-14B | 8001 | Fast structured output, cheap per call |
| Diff classification | Qwen2.5-14B | 8001 | Fast structured output, cheap per call |
| Final analyst memo | Qwen2.5-72B | 8000 | Quality matters for judge-facing output |
| Embeddings | BGE-large-en-v1.5 | 8002 | AMD GPU batch, sub-second per document |
| Reranking | BGE-reranker-large | 8003 | AMD GPU batch, sub-second per query |

72B is used only in the memo node. All other LLM calls use 14B. Running 72B for every agent call would exhaust the $100 credit during development.

## Environment Variables

Copy `configs/.env.example` to `.env` in any service directory. Never commit `.env` files.

`SEC_USER_AGENT` is required by SEC EDGAR and must be set to: `FinContextAgent/0.1 your-email@example.com`. Requests without this header are blocked by EDGAR.

## Compliance Rules (never break)

- Every factual claim in a memo must have a `[citation_id]` referencing a retrieved chunk
- Never generate `buy`, `sell`, `hold`, or `short` as actionable recommendations
- Every memo must end with a research disclaimer: outputs are research assistance, not investment advice
- Risk scores must include `confidence` (0.0–1.0) and a `citations` list — bare scores are invalid
