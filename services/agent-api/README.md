# services/agent-api

FastAPI service that runs the 4-node LangGraph financial analysis workflow.

## What this service does

- Receives portfolio upload and analysis requests from the React UI via HTTPS
- Runs the LangGraph agent graph: portfolio_context_planner → filing_retrieval → disclosure_change → analyst_memo
- Calls the Inference Gateway for all LLM, embedding, and reranking operations
- Reads and writes SQLite for portfolio metadata, job status, cached analysis results, and findings
- Reads Qdrant for vector retrieval during the filing_retrieval node
- Streams SSE tokens to the React UI for the chat endpoint

## Stack

- Python 3.12
- FastAPI (API framework + SSE streaming + CORS middleware)
- LangGraph (agent graph orchestration)
- Pydantic v2 (request/response validation + agent state schema)
- httpx (async HTTP client for Inference Gateway calls)
- qdrant-client (Qdrant vector search)
- sqlite3 (built-in, for metadata, BM25 FTS5, and cached results)

## File Structure

```
services/agent-api/
  main.py                 # FastAPI app — routes, CORS, optional bearer-token auth
  app/
    graph.py              # LangGraph StateGraph — 4 nodes in linear sequence
    retrieval.py          # Hybrid BM25 + Qdrant + RRF + reranker pipeline
    agents/
      portfolio_context_planner.py  # Node 1: load portfolio, build retrieval plan
      filing_retrieval.py           # Node 2: run hybrid retrieval
      disclosure_change.py          # Node 3: classify disclosure language changes
      analyst_memo.py               # Node 4: risk scores, memo, citation verification
    clients/
      gateway.py          # httpx client to Inference Gateway (LLM/embed/rerank)
      qdrant.py           # Qdrant filtered vector search client
      db.py               # SQLite: portfolios, holdings, jobs, findings, chunks, results cache
  tests/
    test_retrieval.py     # Unit tests: section diversity filter
    test_nodes.py         # Unit tests: disclosure heuristic, memo fallback
    integration/
      test_graph.py       # Integration test: full graph run (needs Qdrant + SQLite)
  requirements.txt
  pytest.ini
```

## Running

```bash
# First time: create virtual env and install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Apply schema (first time or after schema.sql changes)
sqlite3 ../../fincontext.db < ../../infra/schema.sql

# Development
INFERENCE_GATEWAY_URL=http://localhost:8080 \
QDRANT_URL=http://localhost:6333 \
SQLITE_DB_PATH=../../fincontext.db \
uvicorn main:app --host 0.0.0.0 --port 8090 --reload

# Tests (no live services required — mocked)
pytest tests/ -x                                   # all, stop on first failure
pytest tests/test_nodes.py -x                      # node unit tests only
pytest tests/integration/ -x                       # integration tests (needs Qdrant + SQLite)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INFERENCE_GATEWAY_URL` | `http://localhost:8080` | Inference Gateway base URL |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST URL |
| `QDRANT_COLLECTION` | `fincontext_chunks` | Qdrant collection name |
| `SQLITE_DB_PATH` | `./fincontext.db` | SQLite database path |
| `AGENT_API_KEY` | *(empty — auth disabled)* | If set, all write endpoints require `Authorization: Bearer <key>` |
| `CORS_ORIGINS` | `https://*.hf.space,http://localhost:5173` | Comma-separated CORS origins |

## Key Design Decisions

**Results are cached after analysis.** After the LangGraph graph completes, the full
`AnalysisState` is serialized as JSON and stored in `analysis_jobs.results_json`. The
`GET /api/findings` endpoint reads from this cache — it never re-runs the graph, which
would waste Qwen2.5-72B GPU credits on every React UI poll.

**All model calls go through the Inference Gateway at port 8080.** Never call NVIDIA NIM, embedding, or reranker backends directly. The gateway adds request IDs, logs metrics, and normalizes responses.

**The reasoner model is used only in the analyst_memo node.** All other LLM calls use the smaller planner model (`fincontext-planner`) to keep latency and hosted inference cost under control.

**72B model is used only in the analyst_memo node.** All other LLM calls use the 14B
model (port 8001, `fincontext-planner`). This protects the $100 AMD credit.

**Citation verification is a post-processing step in analyst_memo.** Every `[chunk_id]`
in the generated memo text is verified against retrieved chunks in state. Sentences with
unverified citations are removed.

**Errors are non-fatal.** If a node fails, it sets `state.error` and `state.partial = True`.
The graph continues and returns partial results rather than raising an unhandled exception.

## Endpoints

See `docs/api-contracts.md` for full request/response specifications.

- `GET /health` — service + dependency health
- `POST /api/portfolio/upload` — CSV upload → SQLite
- `POST /api/analyze` — start async analysis job
- `GET /api/jobs/{job_id}` — poll job status and progress
- `GET /api/findings/{portfolio_id}` — get analysis results
- `GET /api/diff/{ticker}` — get disclosure changes for a ticker
- `POST /api/chat` — SSE streaming citation-backed Q&A
- `GET /api/documents/{ticker}` — list ingested documents
- `GET /api/benchmark/metrics` — inference performance metrics
