# Milestones

Build phase: May 11–19, 2026. Two developers. $100 AMD Developer Cloud credit.

## Pre-Build Phase (Before May 11 — do this NOW)

These tasks must be completed before the official build phase starts. They are not optional.

### Task 1: AMD Developer Cloud VM provisioned and GPU services running

```bash
# On AMD VM
# Install ROCm following AMD documentation
# Install Docker and docker-compose
cd fincontext-agent/infra/amd-gpu
docker compose up -d
curl http://localhost:8000/health      # vLLM 72B ready
curl http://localhost:8001/health      # vLLM 14B ready
curl http://localhost:6333/healthz     # Qdrant ready
```

Expected time: 4–6 hours (most of this is model download time — 72B is ~140 GB).

### Task 2: EDGAR filings pre-ingested for all demo tickers

```bash
cd fincontext-agent/services/ingestion-worker
python ingest.py --tickers AMD,NVDA,MSFT,JPM,TSLA \
                 --filing-types 10-K,10-Q \
                 --years 4
```

Expected output:
- ~50 documents parsed
- ~12,000–18,000 chunks stored in Qdrant
- ~12,000–18,000 chunk metadata rows in SQLite with FTS5 index
- Both teammates should be able to load the Qdrant snapshot and reproduce

Expected time: 3–5 hours (mostly EDGAR download + embedding generation).

### Task 3: Retrieval verified manually

Before writing any agent code, verify the retrieval pipeline works:
```bash
# Quick test: search for AMD supply chain risk
python -c "
from services.ingestion_worker.vector_store import search
results = search('supply chain third party manufacturing risk', tickers=['AMD'], filing_types=['10-K'])
for r in results[:3]:
    print(r.citation_anchor, '|', r.text[:100])
"
```

Expected: 3 results returned, citation anchors make sense, text is relevant to supply chain.

### Deliverable: Everything listed above working before May 11.

---

## Day 1 — May 11: Infrastructure and Skeleton

**Owner split:** Both developers together on AMD setup, then split.

### Developer A: Agent API skeleton
- [ ] Create `services/agent-api/` directory structure
- [ ] FastAPI app with health endpoint: `GET /health → {"status": "ok", "gpu": "AMD MI300X"}`
- [ ] FastAPI portfolio upload endpoint: `POST /api/portfolio/upload` — read CSV, write to SQLite, return `portfolio_id`
- [ ] Stub for `POST /api/analyze` — creates a job record in SQLite, returns `job_id`, runs empty graph
- [ ] Stub for `GET /api/jobs/{job_id}` — returns job status from SQLite
- [ ] `AnalysisState` and all schema models in `packages/schemas/python/state.py`
- [ ] SQLite schema applied: `sqlite3 fincontext.db < infra/schema.sql`

### Developer B: Inference Gateway + Demo UI skeleton
- [ ] Create `services/inference-gateway/` with FastAPI
- [ ] Routes: `POST /v1/chat/completions`, `POST /v1/embeddings`, `POST /v1/rerank`, `GET /health`
- [ ] Each route proxies to the appropriate vLLM/TEI port with request ID logging
- [ ] Create `apps/demo-ui/` with basic Gradio app
- [ ] Gradio tab 1: Portfolio upload (CSV file input → POST to Agent API → show holdings table)
- [ ] Gradio tab 2: Analysis (button → POST to Agent API → poll job status → show "Analysis complete")

### Day 1 Deliverable
- Portfolio CSV can be uploaded via Gradio, appears in SQLite, Gradio shows the holdings table
- `GET /health` returns 200 from both Agent API and Inference Gateway
- vLLM and Qdrant confirmed running on AMD VM

---

## Day 2 — May 12: Retrieval Pipeline

**Note:** Pre-ingested data should already exist in Qdrant from the pre-build phase. This day is about building the retrieval service layer on top of it.

### Developer A: Hybrid retrieval implementation
- [ ] `services/agent-api/app/retrieval.py` — hybrid BM25 + Qdrant retrieval function
- [ ] BM25: SQLite FTS5 query on `chunks_fts` virtual table, return top 50 candidates
- [ ] Vector: Qdrant query with payload filters (ticker, filing_type, date range), return top 50 candidates
- [ ] RRF merge: combine BM25 and vector results with k=60 formula
- [ ] Reranker: call Inference Gateway `/v1/rerank` with merged candidates
- [ ] Diversity filter: max 3 chunks per section per ticker
- [ ] Standalone test: `pytest tests/test_retrieval.py -x` must pass
- [ ] `GET /api/retrieve` endpoint (for debugging during development): accepts query + tickers, returns chunks

### Developer B: Ingestion worker cleanup + SQLite FTS5 index
- [ ] Verify FTS5 index is correctly populated: `SELECT count(*) FROM chunks_fts` should match `chunks` table
- [ ] If pre-ingestion didn't create FTS5 index, build it: `INSERT INTO chunks_fts SELECT text, ticker, filing_type, filed_at, citation_anchor FROM chunks`
- [ ] Fix any parsing issues found in ingested data (section labels, missing fields)
- [ ] Add `GET /api/documents/{ticker}` endpoint — list all ingested documents for a ticker
- [ ] Add Gradio tab 3: Filing Explorer — dropdown to select ticker, show list of ingested documents with filing dates and types

### Day 2 Deliverable
- Retrieval endpoint returns citation-grounded chunks for a test query like "AMD supply chain risk"
- Filing Explorer in Gradio shows all pre-ingested documents for each ticker
- Retrieval tests pass

---

## Day 3 — May 13: LangGraph Graph and Node 1

### Developer A: LangGraph graph wiring + Node 1
- [ ] `services/agent-api/app/graph.py` — StateGraph with 4 nodes (3 stubbed, 1 real)
- [ ] `portfolio_context_planner` node — full implementation (see agent-design.md Node 1)
- [ ] Inference Gateway client: `services/agent-api/app/clients/gateway.py` with `async def chat_completion(model, messages) -> str`
- [ ] Node 1 unit test: mock Gateway + SQLite, verify `retrieval_plan` is populated correctly
- [ ] Wire `POST /api/analyze` to run the graph async (background task)
- [ ] `GET /api/jobs/{job_id}` returns progress stage: "planning" → "retrieving" → "analyzing" → "writing" → "complete"

### Developer B: Gradio real-time job status polling
- [ ] Gradio Analysis tab: after clicking "Analyze", poll `GET /api/jobs/{job_id}` every 2 seconds
- [ ] Show progress stage as text (e.g. "Planning retrieval queries...")
- [ ] When status = "complete", fetch and display a placeholder result (even if it's just "Analysis complete - 5 tickers processed")
- [ ] Test the full round-trip: upload CSV → trigger analysis → watch status change → see completion

### Day 3 Deliverable
- End-to-end: upload portfolio, trigger analysis, see job status progress through stages, reach "complete"
- Node 1 (portfolio_context_planner) produces a valid `RetrievalPlan` for the demo portfolio
- Node 1 unit tests pass

---

## Day 4 — May 14: Nodes 2 and 3 (Retrieval + Disclosure Diff)

This is the most technically important day. The disclosure diff is the hero demo feature.

### Developer A: Node 2 — filing_retrieval
- [ ] `services/agent-api/app/agents/filing_retrieval.py` — full implementation (see agent-design.md Node 2)
- [ ] Parallel retrieval for all tickers with `asyncio.gather`
- [ ] Integration test against real Qdrant: verify retrieval returns chunks for AMD + NVDA
- [ ] Update graph: Node 2 runs after Node 1, state contains `retrieved_chunks` after Node 2

### Developer B: Node 3 — disclosure_change
- [ ] `services/agent-api/app/agents/disclosure_change.py` — full implementation (see agent-design.md Node 3)
- [ ] Section text normalization function (strip boilerplate, XBRL, whitespace)
- [ ] Diff classification with Qwen2.5-14B (structured output)
- [ ] Node 3 unit test: use hardcoded example chunk pairs, verify correct classification
- [ ] `GET /api/diff/{ticker}` endpoint — runs Node 3 on pre-loaded chunks for a ticker, returns `DisclosureChange` list

### Day 4 Deliverable
- `GET /api/diff/AMD` returns a list of classified disclosure changes with citation anchors
- The disclosure diff for AMD shows at least 2-3 real changes between 2022 and 2025 10-K filings
- Graph runs Nodes 1, 2, and 3 in sequence when `/api/analyze` is called

---

## Day 5 — May 15: Node 4 (Analyst Memo) + End-to-End

This is the day the full pipeline runs end-to-end for the first time.

### Developer A: Node 4 — analyst_memo
- [ ] `services/agent-api/app/agents/analyst_memo.py` — full implementation (see agent-design.md Node 4)
- [ ] Risk score computation function
- [ ] Qwen2.5-72B memo generation with citation instructions
- [ ] Citation post-processing: `verify_citations()` function
- [ ] Disclaimer injection (hardcoded, always appended)
- [ ] Node 4 test: mock 72B call, verify disclaimer is always present, verify unsupported citations are removed
- [ ] `GET /api/findings/{portfolio_id}` endpoint — return all findings for a portfolio

### Developer B: Gradio Disclosure Diff and Memo display
- [ ] Gradio tab 3: Disclosure Diff viewer — select ticker + year range → call `/api/diff/{ticker}` → render side-by-side diff with change type labels and materiality badges
- [ ] Gradio tab 4: Analyst Memo — after analysis completes, fetch memo from `/api/findings/{portfolio_id}` → render formatted memo with inline citation references
- [ ] Citation cards: each `[citation_anchor]` in the memo renders as a clickable card showing the chunk text and the SEC EDGAR source URL

### Day 5 Deliverable
- Full pipeline: upload CSV → analyze → see memo with citations in Gradio
- Disclosure diff viewer shows real AMD filing changes with before/after text
- Citation cards link to actual EDGAR URLs

---

## Day 6 — May 16: Risk Scores and Gradio Polish

### Developer A: Risk score panel and API refinements
- [ ] Risk score panel data: ensure `GET /api/findings/{portfolio_id}` includes full risk score breakdown per holding
- [ ] Streaming SSE: implement `POST /api/chat` as a streaming endpoint that streams memo tokens
- [ ] Test streaming with `httpx` SSE client
- [ ] Bug fixes from Day 5 end-to-end run

### Developer B: Gradio Risk panel and streaming chat
- [ ] Gradio tab 5: Risk Scores — table showing per-holding score, score delta, top driver, exposure level
- [ ] Color coding: score 0-20 green, 21-40 yellow, 41-60 orange, 61-80 red, 81-100 dark red
- [ ] Gradio tab 6: Citation-Backed Chat — text input → SSE stream from `/api/chat` → live token rendering → citation cards below
- [ ] Deploy Gradio app to HuggingFace Spaces (even if not all tabs are polished yet — get the public URL early)

### Day 6 Deliverable
- Public HuggingFace Spaces URL works with AMD VM backend
- Risk score panel shows per-holding scores with color coding
- Streaming chat tab shows live token generation from Qwen2.5-72B

---

## Day 7 — May 17: AMD Benchmark Panel + Evals

### Developer A: Benchmark metrics collection
- [ ] Add latency tracking to Inference Gateway: record `time_to_first_token`, `total_latency`, `input_tokens`, `output_tokens` per request
- [ ] `GET /api/benchmark/metrics` endpoint — return aggregated metrics from the last N requests
- [ ] Run benchmark scenarios from `docs/amd-gpu-plan.md`:
  1. Single 10-K analysis (AMD only)
  2. Latest vs prior 10-Q diff (AMD)
  3. 5-stock portfolio review (full demo portfolio)
- [ ] Record and document actual measured values (not estimated)

### Developer B: Gradio benchmark panel + Build-in-Public posts
- [ ] Gradio tab 7: AMD Benchmark — tokens/sec gauge, latency histogram, GPU memory utilization, concurrent request count, cost proxy (GPU-minutes per analysis)
- [ ] Write and post first Build-in-Public post on X/LinkedIn: "Getting vLLM running on AMD ROCm — what worked, what didn't" (tag #AMDDevHackathon)
- [ ] Screenshot the running demo on HuggingFace Spaces for the post

### Day 7 Deliverable
- Real benchmark numbers collected and displayed in Gradio
- First Build-in-Public post published
- End-to-end demo takes under 60 seconds for the demo seed portfolio (pre-ingested data)

---

## Day 8 — May 18: Demo Polish and Submission Prep

### Both developers:
- [ ] Demo run-through: follow the exact demo script from `docs/demo-plan.md` start to finish, fix any blocking issues
- [ ] Gradio UI polish: loading states, error messages, responsive layout
- [ ] HuggingFace Space README — explain the AMD MI300X hardware story, link to AMD Developer Cloud, describe the agent architecture
- [ ] Project README updated with architecture diagram (ASCII is fine), setup instructions, and demo instructions
- [ ] Second Build-in-Public post: "Hybrid BM25 + vector retrieval on financial text — benchmark comparison" (with real numbers)
- [ ] Record a demo video (3-5 minutes) following the demo script

### Day 8 Deliverable
- Demo runs end-to-end without intervention in under 90 seconds
- HuggingFace Space is public and loads correctly
- Demo video recorded

---

## Day 9 — May 19: Final Submission

### Both developers:
- [ ] Final check: all Gradio tabs functional on HuggingFace Spaces
- [ ] Submission write-up on lablab.ai: project description, architecture diagram, AMD GPU story, HuggingFace integration description, demo video link, GitHub repo link
- [ ] Third Build-in-Public post: "AMD MI300X 192 GB VRAM — running Qwen2.5-72B FP16 on a single GPU with real benchmark numbers" (tag #AMDDevHackathon)
- [ ] Verify submission is complete before the hackathon deadline

---

## Stretch Goals (only if Days 1-9 are complete)

Do not start these until the core pipeline is demo-ready.

- Add 8-K filing ingestion for material event alerts
- Add earnings transcript samples (pre-downloaded, parsed)
- Add peer comparison: for each holding, compare risk language against sector peers
- Add historical risk score chart (score over time as filings are analyzed)
- Add PDF parsing for investor presentation PDFs (one specific document only, not general PDF support)
- Add a second portfolio for comparison ("tech-heavy" vs "diversified" demo portfolios)

---

## Time Budget

| Day | Primary risk | Mitigation |
|-----|-------------|------------|
| Pre-build | AMD VM provisioning takes longer than expected | Start immediately, not on May 11 |
| Pre-build | 72B model download is slow | Begin download as first step |
| Day 1-2 | EDGAR HTML parsing is messier than expected | Use only the 5 pre-ingested demo tickers |
| Day 3-4 | LangGraph state mutations cause unexpected behavior | Test each node in complete isolation before graph integration |
| Day 5 | Qwen2.5-72B generates hallucinated citations | Citation post-processor handles this — test it first |
| Day 6-7 | HuggingFace Spaces can't reach AMD VM | Expose Agent API with a tunnel (ngrok or Cloudflare Tunnel as a fallback) |
| Day 8 | Demo run-through reveals blocking issues | Reserve full Day 8 for this — do not add features on Day 8 |
