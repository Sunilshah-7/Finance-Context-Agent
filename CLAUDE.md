# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FinContext Agent — AMD Developer Hackathon 2026 submission (Track 1: AI Agents & Agentic Workflows). A portfolio-aware financial intelligence platform that ingests SEC filings from EDGAR, detects material disclosure changes year-over-year, scores risk per portfolio holding, and produces citation-grounded analyst memos. The app and retrieval stack run behind a public Gradio UI on HuggingFace Spaces, with LLM inference routed through NVIDIA NIM.

**Hackathon constraint: 9-day build phase May 11–19, 2026. Three developers.**

All planning docs are in `docs/`. No application code exists yet — the build phase ends May 11.

## Critical Architecture Decision

App services, storage, retrieval, and orchestration stay compact behind one Agent API. LLM inference is provider-agnostic through the Inference Gateway and currently routes to NVIDIA NIM hosted endpoints. The public demo UI is a Gradio app in `apps/demo-ui/` deployed to HuggingFace Spaces. Do not add a separate edge/API layer or a JavaScript frontend; the project is intentionally optimized for the 9-day hackathon timeline.

## Deployment Architecture

```
Backend host
├── Inference Gateway   port 8080  — FastAPI proxy to NVIDIA NIM + retrieval model backends
├── Agent API           port 8090  — FastAPI + LangGraph, 4-node agent graph
├── NIM reasoner                    Qwen2.5-72B-Instruct compatible endpoint
├── NIM planner                     Qwen2.5-7B-Instruct compatible endpoint
├── Embedding backend               local retrieval embeddings
├── Reranker backend                local reranking/scoring
├── Qdrant              port 6333  — Vector store, Docker, persistent volume
└── SQLite              on-disk    — Metadata: portfolios, holdings, jobs, findings, chunks

HuggingFace Spaces  (public demo, free tier)
└── Gradio app  →  calls Agent API over HTTPS
```

The Inference Gateway is the only external-facing model endpoint. Agent API calls Gateway. Gradio calls Agent API. No service bypasses the Gateway for model calls.

## Repository Layout (target — no code written yet)

```

services/
      agent-api/          # FastAPI + LangGraph 4-node agent graph
      ingestion-worker/   # SEC EDGAR fetch, parse, chunk, embed → Qdrant + SQLite
      inference-gateway/  # FastAPI proxy to NIM, embedding, reranker
apps/
      demo-ui/            # Gradio app — deployed to HuggingFace Spaces
packages/
      schemas/            # Shared Pydantic models (Python) + generated TS types
      evals/              # Retrieval recall, citation precision, latency benchmarks
infra/
      amd-gpu/            # Legacy Docker Compose: local model services + Qdrant
      schema.sql          # SQLite schema
configs/
      .env.example
docs/
```

## Commands

**Start storage services:**
```bash
cp configs/.env.example .env              # fill NIM_API_KEY and app secrets
docker compose -f infra/amd-gpu/docker-compose.yml up -d qdrant
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
git subtree push --prefix apps/demo-ui space main
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
  → reranker backend through Inference Gateway
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

## Model Allocation

| Task | Model | Port | Rationale |
|------|-------|------|-----------|
| Retrieval planning | NIM planner | hosted | Fast structured output, cheaper per call |
| Diff classification | NIM planner | hosted | Fast structured output, cheaper per call |
| Final analyst memo | NIM reasoner | hosted | Quality matters for judge-facing output |
| Embeddings | Local embedding backend | internal | Deterministic retrieval vectors |
| Reranking | Local reranker/scorer | internal | Improves precision after RRF merge |

The reasoner model is used only in the memo node. All other LLM calls use the planner model to control latency and hosted inference cost.

## Environment Variables

Copy `configs/.env.example` to `.env` in any service directory. Never commit `.env` files.

`SEC_USER_AGENT` is required by SEC EDGAR and must be set to: `FinContextAgent/0.1 your-email@example.com`. Requests without this header are blocked by EDGAR.

## Compliance Rules (never break)

- Every factual claim in a memo must have a `[citation_id]` referencing a retrieved chunk
- Never generate `buy`, `sell`, `hold`, or `short` as actionable recommendations
- Every memo must end with a research disclaimer: outputs are research assistance, not investment advice
- Risk scores must include `confidence` (0.0–1.0) and a `citations` list — bare scores are invalid
