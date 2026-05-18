# services/agent-api

FastAPI service that runs the 4-node LangGraph financial analysis workflow.

## What this service does

- Receives portfolio upload and analysis requests from the Gradio UI via HTTPS
- Runs the LangGraph agent graph: portfolio_context_planner → filing_retrieval → disclosure_change → analyst_memo
- Calls the Inference Gateway for all LLM, embedding, and reranking operations
- Reads and writes SQLite for portfolio metadata, job status, and findings
- Reads Qdrant for vector retrieval during the filing_retrieval node
- Streams SSE tokens to the Gradio UI for the chat endpoint

## Stack

- Python 3.12
- FastAPI (API framework + SSE streaming)
- LangGraph (agent graph orchestration)
- Pydantic v2 (request/response validation + agent state schema)
- httpx (async HTTP client for Inference Gateway calls)
- qdrant-client (Qdrant vector search)
- sqlite3 (built-in, for metadata and BM25 FTS5)

## File Structure (target)

```
services/agent-api/
  main.py                 # FastAPI app definition, route mounting
  app/
    graph.py              # LangGraph StateGraph definition — 4 nodes
    retrieval.py          # Hybrid BM25 + Qdrant + reranker function
    agents/
      portfolio_context_planner.py  # Node 1: load portfolio + generate retrieval plan
      filing_retrieval.py           # Node 2: run hybrid retrieval
      disclosure_change.py          # Node 3: classify disclosure language changes
      analyst_memo.py               # Node 4: risk scores + memo + citation verification
    clients/
      gateway.py          # httpx client to Inference Gateway (all LLM/embed/rerank calls)
      qdrant.py           # Qdrant client wrapper with filter helpers
      db.py               # SQLite queries: portfolios, holdings, jobs, findings, chunks
  tests/
    test_retrieval.py     # Unit tests for hybrid retrieval (mocked Qdrant + SQLite)
    test_nodes.py         # Unit tests for each agent node (mocked Gateway)
    integration/
      test_graph.py       # Full graph integration test with real Qdrant
  requirements.txt
```

## Running

```bash
# First time: create virtual env and install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Development
uvicorn main:app --host 0.0.0.0 --port 8090 --reload

# Tests
pytest tests/ -x                                   # all, stop on first failure
pytest tests/test_nodes.py -x                      # node unit tests only
pytest tests/integration/ -x                       # integration tests (needs Qdrant running)
```

## Key Design Decisions

**Agents never call each other directly.** Each node function has the signature `async def node_name(state: AnalysisState) -> AnalysisState`. LangGraph handles routing. Nodes read from state, perform their work, and return updated state.

**All model calls go through the Inference Gateway at port 8080.** Never call NVIDIA NIM, embedding, or reranker backends directly. The gateway adds request IDs, logs metrics, and normalizes responses.

**The reasoner model is used only in the analyst_memo node.** All other LLM calls use the smaller planner model (`fincontext-planner`) to keep latency and hosted inference cost under control.

**Citation verification is a post-processing step in analyst_memo, not a separate agent.** Every `[chunk_id]` in the generated memo text is verified against the retrieved chunks in state. Sentences with unverified citations are removed.

**Errors are non-fatal.** If a node fails, it sets `state.error` and `state.partial = True`. The graph continues and returns partial results rather than raising an unhandled exception.

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
