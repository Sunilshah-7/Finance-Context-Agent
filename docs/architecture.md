# Architecture

## Decision: Single-VM Architecture

The MVP runs compute, storage, retrieval, and orchestration on one AMD Developer Cloud VM. This keeps the backend simple: localhost service calls, one database file, one vector store, one GPU host, and one public React Static Space on HuggingFace Spaces.

The frontend is a Vite React app on HuggingFace Static Spaces. The original fast-ship plan used Gradio, but the project moved to React after the deadline to get a more polished analyst-console UI while keeping HuggingFace integration.

## High-Level Architecture

```
User (browser / React UI)
  │
  │  HTTPS
  ▼
HuggingFace Spaces — React Static Space (apps/demo-ui/)
  │
  │  HTTPS  →  AMD_VM_PUBLIC_IP:8090
  ▼
AMD Developer Cloud VM
  ├── Agent API (port 8090) ─────────────────────────────────────┐
  │     FastAPI + LangGraph                                       │
  │     4-node agent graph                                        │
  │     Reads/writes SQLite for metadata                         │
  │     Reads/writes Qdrant for retrieval                        │
  │     Calls Inference Gateway for all model work               │
  │                                                               │
  ├── Inference Gateway (port 8080) ←────────────────────────────┘
  │     FastAPI proxy
  │     Routes completions → vLLM 72B or vLLM 14B
  │     Routes embeddings → BGE embedding service
  │     Routes rerank → BGE reranker service
  │     Logs latency, token counts, error rates
  │
  ├── vLLM reasoner (port 8000)     Qwen2.5-72B-Instruct, FP16, ROCm
  ├── vLLM planner (port 8001)      Qwen2.5-14B-Instruct, FP16, ROCm
  ├── Embedding service (port 8002) BAAI/bge-large-en-v1.5, TEI or vLLM
  ├── Reranker service (port 8003)  BAAI/bge-reranker-large, TEI
  ├── Qdrant (port 6333)            Docker, persistent volume, HNSW index
  └── SQLite (on-disk)              Metadata: portfolios, holdings, jobs, findings, chunks
```

## Service Responsibilities

### Agent API (`services/agent-api/`)

The brain of the system. Receives analysis requests from the React UI, runs the 4-node LangGraph graph, coordinates retrieval and model calls through the Inference Gateway, and writes findings back to SQLite.

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

A lightweight FastAPI proxy that sits between the Agent API and the model-serving processes. Its job is to:
- Route requests to the correct model based on the `model` field in the request
- Add request IDs and log latency, token counts, and errors
- Normalize responses into a consistent OpenAI-compatible format
- Expose `/health` and `/metrics` endpoints

This service makes the Agent API independent of which specific model is loaded. Swapping models during development only requires updating the Gateway's routing config.

### Demo UI (`apps/demo-ui/`)

A Vite React app that provides the judge-facing interface. It communicates with the Agent API over HTTPS using the AMD VM's public IP. It is deployed as a HuggingFace Static Space.

Key UI tabs:
1. Portfolio Upload — CSV upload, holdings display
2. Analysis — trigger analysis, job status stream
3. Disclosure Diff — side-by-side filing comparison with change labels
4. Risk Scores — per-holding score table with drivers
5. Analyst Memo — streaming memo display with citation cards
6. AMD Benchmark — tokens/sec, latency, GPU memory utilization panel

## Data Flow: Full Request Lifecycle

### Portfolio Upload

```
User uploads CSV
  → React UI calls POST /api/portfolio/upload
  → Agent API validates CSV (required columns: ticker, shares, market_value)
  → Agent API writes to SQLite: portfolios, holdings rows
  → Calls ticker-to-CIK resolver for each holding (EDGAR company_tickers.json cache)
  → Returns portfolio_id to React UI
```

### Portfolio Analysis (async)

```
User clicks "Analyze Latest Filings"
  → React UI calls POST /api/analyze with portfolio_id
  → Agent API creates analysis_jobs row (status=queued), returns job_id immediately
  → Background task starts LangGraph graph

  Graph execution:
    Node 1: portfolio_context_planner
      - Loads holdings from SQLite
      - Computes weights and sector exposure
      - Generates retrieval_plan (structured Qwen2.5-14B output)

    Node 2: filing_retrieval
      - BM25 search on SQLite FTS5 chunks_fts table
      - Vector search on Qdrant with ticker/filing_type/date filters
      - RRF merge → BGE reranker → diversity filter
      - Writes retrieved_chunks to AnalysisState

    Node 3: disclosure_change
      - Groups chunks by ticker + section + filing date
      - Pairs same-section chunks from different years
      - Classifies changes with Qwen2.5-14B
      - Writes disclosure_changes to AnalysisState

    Node 4: analyst_memo
      - Computes risk scores per holding
      - Generates structured memo with Qwen2.5-72B
      - Citation post-processing: removes unsupported claims
      - Writes memo, risk_scores, citation_pass_rate to AnalysisState

  Agent API writes findings to SQLite
  Agent API sets analysis_jobs.status = "completed"
  Agent API sets analysis_jobs.completed_at = now()
```

### Disclosure Diff (synchronous, pre-ingested data)

```
User navigates to Disclosure Diff tab, selects AMD + section
  → React UI calls GET /api/diff/AMD?section=Item+1A&year_a=2023&year_b=2025
  → Agent API queries SQLite for chunk records matching ticker + section + filing years
  → Runs disclosure_change node logic on those specific chunks (no full graph needed)
  → Returns DisclosureChange list with classification labels and citation anchors
  → React UI renders side-by-side diff with change labels highlighted
```

### Citation-Backed Chat (synchronous, streaming)

```
User types "What changed in supply-chain risk for AMD?"
  → React UI opens SSE connection to POST /api/chat
  → Agent API runs mini graph: context_planner → filing_retrieval → memo (no diff node)
  → Memo node streams tokens via SSE
  → React UI renders tokens as they arrive
  → At end of stream, React UI renders citation cards below the answer
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

- Static browser apps cannot keep `AGENT_API_KEY` secret. For the public demo, Agent API should expose demo-safe frontend endpoints with CORS and rate limiting, while private/admin operations can still require bearer auth.
- The AMD VM's firewall should expose only port 8090 (Agent API) externally; ports 8000, 8001, 8002, 8003, 8080, and 6333 should be internal-only
- The `SEC_USER_AGENT` header must identify the application and include a contact email — EDGAR will block requests that omit it or use a generic user agent

## Why This Beats the NVIDIA Story

AMD MI300X has 192 GB of HBM3 VRAM. Qwen2.5-72B in FP16 requires approximately 144 GB of VRAM. A single MI300X runs it without tensor parallelism. NVIDIA H100 SXM has 80 GB — it cannot hold a 72B FP16 model and would require a multi-GPU setup with tensor-parallel configuration.

Our demo shows:
- Full 10-K text (average 200–350 pages, ~150,000 tokens) processed in a single context window pass
- `--max-model-len 65536` in vLLM, using the full long-context capability
- No chunked multi-pass inference, no context fragmentation, no multi-GPU orchestration overhead

For the benchmark panel, record and display:
- Tokens per second (input + output)
- Time to first token (ms)
- GPU memory utilization (%)
- Number of concurrent analysis requests handled
- Cost proxy: GPU-minutes per full portfolio analysis
