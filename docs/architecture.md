# Architecture

## Decision: Provider-Agnostic Inference Architecture

The MVP keeps app orchestration, retrieval, metadata, and the public demo small and hackathon-friendly, while LLM inference is routed through NVIDIA NIM hosted endpoints. The key boundary is the Inference Gateway: application code never depends directly on a specific serving vendor.

The frontend is a Gradio app on HuggingFace Spaces. It satisfies the hackathon's HuggingFace integration requirement, deploys with a `git push`, and is publicly accessible to judges.

## High-Level Architecture

```
User (browser / Gradio UI)
  │
  │  HTTPS
  ▼
HuggingFace Spaces — Gradio app (apps/demo-ui/)
  │
  │  HTTPS  →  Agent API
  ▼
Backend host
  ├── Agent API (port 8090) ─────────────────────────────────────┐
  │     FastAPI + LangGraph                                       │
  │     4-node agent graph                                        │
  │     Reads/writes SQLite for metadata                         │
  │     Reads/writes Qdrant for retrieval                        │
  │     Calls Inference Gateway for all model work               │
  │                                                               │
  ├── Inference Gateway (port 8080) ←────────────────────────────┘
  │     FastAPI proxy
  │     Routes completions → NVIDIA NIM hosted inference
  │     Routes embeddings → local embedding service
  │     Routes rerank → reranker service or local scoring
  │     Logs latency, token counts, error rates
  │
  ├── NVIDIA NIM reasoner           Qwen2.5-72B-Instruct compatible endpoint
  ├── NVIDIA NIM planner            Qwen2.5-7B-Instruct compatible endpoint
  ├── Embedding service             Local retrieval embeddings
  ├── Reranker service              Reranking retrieval candidates
  ├── Qdrant (port 6333)            Docker, persistent volume, HNSW index
  └── SQLite (on-disk)              Metadata: portfolios, holdings, jobs, findings, chunks
```

## Service Responsibilities

### Agent API (`services/agent-api/`)

The brain of the system. Receives analysis requests from the Gradio UI, runs the 4-node LangGraph graph, coordinates retrieval and model calls through the Inference Gateway, and writes findings back to SQLite.

Endpoints:
- `POST /api/portfolio/upload` — validate and store a portfolio CSV in SQLite
- `POST /api/analyze` — start an analysis job, return a job ID immediately, run analysis async
- `GET /api/jobs/{job_id}` — poll job status and progress stage
- `POST /api/chat` — synchronous citation-backed Q&A, streams SSE tokens
- `GET /api/findings/{portfolio_id}` — return all findings for a portfolio
- `GET /api/diff/{ticker}` — return disclosure changes for a ticker

### Ingestion Worker (`services/ingestion-worker/`)

A Python script (not a long-running server) that is run before the demo and on-demand for new tickers. Fetches SEC EDGAR HTML filings, parses them into sections, chunks them with citation anchors, generates embeddings via the Inference Gateway, and upserts into Qdrant and SQLite.

This worker is invoked as a CLI tool:
```bash
python ingest.py --tickers AMD,NVDA --filing-types 10-K --years 3
```

For MVP, it only processes HTML filings from EDGAR. PDF parsing is not implemented.

### Inference Gateway (`services/inference-gateway/`)

A lightweight FastAPI proxy that sits between the Agent API and model providers. Its job is to:
- Route requests to the correct model based on the `model` field in the request
- Add request IDs and log latency, token counts, and errors
- Normalize responses into a consistent OpenAI-compatible format
- Expose `/health` and `/metrics` endpoints

This service makes the Agent API independent of which specific model or provider is used. Swapping between NVIDIA NIM and another OpenAI-compatible backend only requires updating the Gateway's routing config.

### Demo UI (`apps/demo-ui/`)

A Gradio app that provides the judge-facing interface. It communicates with the Agent API over HTTPS. It is deployed to HuggingFace Spaces.

Key Gradio tabs:
1. Portfolio Upload — CSV upload, holdings display
2. Analysis — trigger analysis, job status stream
3. Disclosure Diff — side-by-side filing comparison with change labels
4. Risk Scores — per-holding score table with drivers
5. Analyst Memo — streaming memo display with citation cards
6. Inference Metrics — tokens/sec, latency, request volume, and provider health

## Data Flow: Full Request Lifecycle

### Portfolio Upload

```
User uploads CSV
  → Gradio calls POST /api/portfolio/upload
  → Agent API validates CSV (required columns: ticker, shares, market_value)
  → Agent API writes to SQLite: portfolios, holdings rows
  → Calls ticker-to-CIK resolver for each holding (EDGAR company_tickers.json cache)
  → Returns portfolio_id to Gradio UI
```

### Portfolio Analysis (async)

```
User clicks "Analyze Latest Filings"
  → Gradio calls POST /api/analyze with portfolio_id
  → Agent API creates analysis_jobs row (status=queued), returns job_id immediately
  → Background task starts LangGraph graph

  Graph execution:
    Node 1: portfolio_context_planner
      - Loads holdings from SQLite
      - Computes weights and sector exposure
      - Generates retrieval_plan (structured planner-model output)

    Node 2: filing_retrieval
      - BM25 search on SQLite FTS5 chunks_fts table
      - Vector search on Qdrant with ticker/filing_type/date filters
      - RRF merge → reranker → diversity filter
      - Writes retrieved_chunks to AnalysisState

    Node 3: disclosure_change
      - Groups chunks by ticker + section + filing date
      - Pairs same-section chunks from different years
      - Classifies changes with the planner model
      - Writes disclosure_changes to AnalysisState

    Node 4: analyst_memo
      - Computes risk scores per holding
      - Generates structured memo with the reasoner model
      - Citation post-processing: removes unsupported claims
      - Writes memo, risk_scores, citation_pass_rate to AnalysisState

  Agent API writes findings to SQLite
  Agent API sets analysis_jobs.status = "completed"
  Agent API sets analysis_jobs.completed_at = now()
```

### Disclosure Diff (synchronous, pre-ingested data)

```
User navigates to Disclosure Diff tab, selects AMD + section
  → Gradio calls GET /api/diff/AMD?section=Item+1A&year_a=2023&year_b=2025
  → Agent API queries SQLite for chunk records matching ticker + section + filing years
  → Runs disclosure_change node logic on those specific chunks (no full graph needed)
  → Returns DisclosureChange list with classification labels and citation anchors
  → Gradio renders side-by-side diff with change labels highlighted
```

### Citation-Backed Chat (synchronous, streaming)

```
User types "What changed in supply-chain risk for AMD?"
  → Gradio opens SSE connection to POST /api/chat
  → Agent API runs mini graph: context_planner → filing_retrieval → memo (no diff node)
  → Memo node streams tokens via SSE
  → Gradio renders tokens as they arrive
  → At end of stream, Gradio renders citation cards below the answer
```

## Data Stores

| Store | What lives here | Technology | Backup strategy |
|-------|----------------|------------|-----------------|
| Qdrant | Chunk vectors + full payload metadata | Docker volume | Qdrant snapshot export |
| SQLite | Portfolios, holdings, documents, chunk metadata (text + citation anchors), jobs, findings | File | cp fincontext.db fincontext.backup.db |
| Local disk | Raw EDGAR HTML filings (optional, for re-parsing) | Directory | Not critical, EDGAR is the source of truth |

Note: The chunk text is stored in both SQLite (for BM25 FTS5) and Qdrant payload. This duplication is intentional — SQLite FTS5 gives high-quality BM25 scores; Qdrant gives vector search. Keeping both on the same machine means the join between BM25 results and vector results happens in Python with no network overhead.

## Pre-Ingestion Snapshot Strategy

After the ingestion worker successfully processes all demo tickers, create a shareable snapshot:

```bash
# Qdrant snapshot
curl -X POST "http://localhost:6333/collections/fincontext_chunks/snapshots"
# Downloads a .snapshot file — share this file with teammates

# SQLite backup
cp fincontext.db fincontext_demo_snapshot.db
```

Both teammates should restore from the same snapshot before demo day to ensure identical data state.

## Security Notes (minimal, hackathon scope)

- The Agent API should require a simple bearer token (`AGENT_API_KEY` env var) so the HuggingFace Spaces UI can authenticate without exposing the VM directly
- The backend firewall should expose only the Agent API externally; Gateway, Qdrant, SQLite, and local retrieval services should be internal-only
- The `SEC_USER_AGENT` header must identify the application and include a contact email — EDGAR will block requests that omit it or use a generic user agent

## Why The Gateway Matters

The original plan tied the demo to a specific local GPU stack. The current design treats inference as a replaceable provider behind one OpenAI-compatible Gateway contract.

Our demo shows:
- Agent workflow is unchanged when inference moves to NVIDIA NIM
- Model requests, latency metrics, errors, and retries are centralized
- Retrieval and citation grounding stay local and auditable
- The system can later move to local GPU serving without changing Agent API code

For the inference metrics panel, record and display:
- Tokens per second (input + output)
- Time to first token (ms)
- Provider/model used for each request
- Number of concurrent analysis requests handled
- Cost proxy: hosted inference calls per full portfolio analysis
