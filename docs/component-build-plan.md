# Component Build Plan

Build components in this exact order. Each step produces a testable deliverable. Do not start step N+1 until step N has a passing test.

---

## Step 0: Environment and Schema (Pre-Build Phase)

### AMD VM Setup

```bash
# Verify ROCm is installed and GPU is visible
rocm-smi
# Expected: shows GPU device with memory info

# Verify Docker is installed
docker --version && docker compose version

# Start all GPU services
cd infra/amd-gpu
docker compose up -d

# Verify each service is healthy
curl http://localhost:8000/health      # vLLM 72B — may take 3-5 min to load
curl http://localhost:8001/health      # vLLM 14B
curl http://localhost:8002/health      # embedding service
curl http://localhost:8003/health      # reranker service
curl http://localhost:6333/healthz     # Qdrant
```

### SQLite Schema

```bash
sqlite3 fincontext.db < infra/schema.sql
# Verify tables were created
sqlite3 fincontext.db ".tables"
# Expected: portfolios holdings documents chunks chunks_fts analysis_jobs findings
```

Schema additions for FTS5 (add to schema.sql if not already there):
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    ticker UNINDEXED,
    filing_type UNINDEXED,
    filed_at UNINDEXED,
    citation_anchor UNINDEXED,
    content='chunks',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text, ticker, filing_type, filed_at, citation_anchor)
    VALUES (new.rowid, new.text, new.ticker, new.filing_type, new.filed_at, new.citation_anchor);
END;
```

### Qdrant Collection

```python
# Run once to create the collection
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")
client.create_collection(
    collection_name="fincontext_chunks",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)
# Verify
print(client.get_collection("fincontext_chunks"))
```

---

## Step 1: Shared Schemas (`packages/schemas/python/`)

Build shared schemas before any service code. All service code imports from here.

```
packages/schemas/python/
  __init__.py
  state.py      # AnalysisState and all subtypes (copy from agent-design.md)
  db.py         # SQLite row types for portfolios, holdings, documents, chunks, jobs, findings
  api.py        # FastAPI request/response models for each endpoint
```

Test: `python -c "from packages.schemas.python.state import AnalysisState; print('ok')"` — must not error.

---

## Step 2: Ingestion Worker (`services/ingestion-worker/`)

Build this second because retrieval depends on data existing in Qdrant and SQLite.

### 2a. SEC EDGAR Client (`worker/sec_client.py`)

Responsibilities:
- Download and cache `company_tickers.json` (ticker → CIK mapping)
- Fetch company submission metadata from `https://data.sec.gov/submissions/CIK{cik_padded}.json`
- Find filings of a given type (10-K, 10-Q) within a date range
- Download the primary document for a filing from the EDGAR Archives
- Rate limit to 10 requests/second
- Set `User-Agent: FinContextAgent/0.1 your-email@example.com` on every request

```python
class EDGARClient:
    BASE_URL = "https://data.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

    def __init__(self, user_agent: str, rate_limit: float = 10.0):
        self.session = httpx.AsyncClient(
            headers={"User-Agent": user_agent},
            timeout=30.0
        )
        self.rate_limiter = AsyncRateLimiter(rate_limit)

    async def get_cik(self, ticker: str) -> str: ...
    async def get_filings(self, cik: str, form_type: str, from_date: str, to_date: str) -> list[FilingRef]: ...
    async def download_filing(self, cik: str, accession_number: str) -> str:  # returns HTML text
```

Test: `pytest worker/tests/test_sec_client.py -x` — must correctly resolve AMD ticker to CIK `0000002488`.

### 2b. HTML Parser (`worker/parsers/sec_html.py`)

Responsibilities:
- Accept raw EDGAR HTML text
- Extract sections by item label (Item 1, Item 1A, Item 7, Item 7A, Item 8)
- Handle multiple EDGAR HTML formats (pre-2018 and post-2018)
- Return a list of `Section(label, title, text, tables)` objects
- Strip XBRL inline tags, page headers, and navigation elements

EDGAR item label detection patterns:
```python
ITEM_PATTERNS = [
    r'<[^>]+id="[^"]*item[\s_-]?1a[^"]*"',   # id attribute matching
    r'>item\s+1a\.?\s*<',                       # text content matching (case-insensitive)
    r'>risk\s+factors<',                        # section title fallback
]
```

Section order to extract (in priority order):
1. `Item 1A` — Risk Factors (most important for disclosure diff)
2. `Item 7` — MD&A (second most important)
3. `Item 7A` — Quantitative Disclosures
4. `Item 1` — Business description
5. `Item 8` — Financial statements (tables only for MVP)

Test: Use a saved AMD 2024 10-K HTML file. Verify Item 1A is extracted with at least 1000 words.

### 2c. Chunker (`worker/chunking.py`)

Responsibilities:
- Accept a `Section` object
- Split into chunks of 600-1000 tokens using a tokenizer (use `tiktoken` or HuggingFace tokenizer)
- Overlap: 100 tokens between consecutive chunks
- Never split a table across chunks — tables become their own chunks
- Assign `citation_anchor`: `f"{ticker} {filing_type} {section_label} paragraph {para_idx}"`
- Compute `text_hash`: `hashlib.sha256(chunk_text.encode()).hexdigest()[:16]`
- Return `list[ChunkInput]` with all fields needed for SQLite + Qdrant upsert

Test: Chunk a 5000-word section, verify chunk sizes are within range, verify overlaps exist.

### 2d. Embedding Generator (`worker/embeddings.py`)

Responsibilities:
- Accept a list of chunk texts (up to 256 at once)
- POST to `http://localhost:8002/embeddings` (Inference Gateway → TEI embedding service)
- Return list of 1024-dimensional float vectors
- Handle rate limits and retries (3 retries with exponential backoff)

```python
async def embed_batch(texts: list[str], gateway_url: str) -> list[list[float]]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{gateway_url}/v1/embeddings",
            json={"input": texts, "model": "fincontext-embedding"},
            timeout=60.0
        )
        return [d["embedding"] for d in response.json()["data"]]
```

Test: Embed 10 texts, verify output shape is (10, 1024).

### 2e. Vector Store Writer (`worker/vector_store.py`)

Responsibilities:
- Accept chunks with embeddings
- Upsert to Qdrant `fincontext_chunks` collection with all required payload fields
- Upsert to SQLite `chunks` table (and FTS5 trigger handles the FTS index)
- Handle duplicates: check `text_hash` in SQLite before upserting — skip if already exists

```python
async def upsert_chunks(chunks: list[ChunkWithEmbedding], qdrant_client, db_conn):
    # Check for duplicates
    existing_hashes = get_existing_hashes(db_conn, [c.text_hash for c in chunks])
    new_chunks = [c for c in chunks if c.text_hash not in existing_hashes]
    
    if not new_chunks:
        return
    
    # SQLite insert
    db_conn.executemany("INSERT INTO chunks (...) VALUES (...)", [...])
    
    # Qdrant upsert
    qdrant_client.upsert(
        collection_name="fincontext_chunks",
        points=[PointStruct(
            id=c.chunk_id,
            vector=c.embedding,
            payload={
                "chunk_id": c.chunk_id,
                "ticker": c.ticker,
                "filing_type": c.filing_type,
                "filed_at": c.filed_at,
                "section": c.section,
                "citation_anchor": c.citation_anchor,
                "text": c.text,  # stored in payload for reranker input
                "source_url": c.source_url,
                ...
            }
        ) for c in new_chunks]
    )
```

### 2f. Main Ingest Script (`worker/ingest.py`)

Ties all components together:
```bash
python ingest.py --tickers AMD,NVDA,MSFT,JPM,TSLA \
                 --filing-types 10-K,10-Q \
                 --years 4 \
                 --db-path ../../fincontext.db \
                 --qdrant-url http://localhost:6333 \
                 --gateway-url http://localhost:8080
```

Processes each ticker in sequence (not parallel — EDGAR rate limits). For each ticker:
1. Resolve ticker to CIK
2. Find filings of requested types within date range
3. For each filing: download → parse → chunk → embed → upsert

Progress output:
```
[AMD] Resolved to CIK 0000002488
[AMD] Found 8 filings (4 10-K, 4 10-Q)
[AMD] Processing 10-K filed 2025-02-14...
[AMD] Parsed 6 sections, 847 chunks
[AMD] Embedded 847 chunks (3 batches)
[AMD] Upserted 847 chunks to Qdrant and SQLite
...
Done. Total: 50 documents, 14,392 chunks.
```

---

## Step 3: Inference Gateway (`services/inference-gateway/`)

Build before the agent API because the agent API depends on it.

```
services/inference-gateway/
  main.py
  router.py       # Route requests by model name to correct backend
  middleware.py   # Request ID generation, latency logging
  models.py       # Pydantic models for /v1/chat/completions etc.
```

Routing logic:
```python
MODEL_ROUTING = {
    "fincontext-reasoner": "http://localhost:8000",   # vLLM 72B
    "fincontext-planner":  "http://localhost:8001",   # vLLM 14B
    "fincontext-embedding": "http://localhost:8002",  # TEI embedding
    "fincontext-reranker":  "http://localhost:8003",  # TEI reranker
}
```

Each request gets a `X-Request-Id` header. Every response is logged: `{request_id, model, input_tokens, output_tokens, latency_ms, status_code}`. These logs feed the benchmark panel.

Test: `pytest tests/test_gateway.py -x` — mock backend services, verify correct routing and latency logging.

---

## Step 4: Agent API (`services/agent-api/`)

Build in this internal order: FastAPI skeleton → SQLite client → retrieval module → agent nodes → graph wiring.

```
services/agent-api/
  main.py              # FastAPI app, route definitions
  app/
    graph.py           # LangGraph StateGraph definition
    retrieval.py       # Hybrid BM25 + Qdrant + reranker function
    agents/
      portfolio_context_planner.py
      filing_retrieval.py
      disclosure_change.py
      analyst_memo.py
    clients/
      gateway.py       # httpx client to Inference Gateway
      qdrant.py        # Qdrant client wrapper
      db.py            # SQLite queries
  tests/
    test_retrieval.py
    test_nodes.py      # unit tests for each agent node
    integration/
      test_graph.py    # full graph integration test with real Qdrant
```

### 4a. SQLite client (`app/clients/db.py`)

```python
def get_holdings(db_path: str, portfolio_id: str) -> list[Holding]: ...
def create_portfolio(db_path: str, name: str) -> str: ...
def upsert_holding(db_path: str, portfolio_id: str, holding: HoldingInput) -> str: ...
def create_job(db_path: str, portfolio_id: str, job_type: str) -> str: ...
def update_job_status(db_path: str, job_id: str, status: str, stage: str | None = None): ...
def save_findings(db_path: str, findings: list[Finding]): ...
```

### 4b. Retrieval module (`app/retrieval.py`)

```python
async def hybrid_retrieve(
    query: str,
    tickers: list[str],
    filing_types: list[str],
    date_range: tuple[str, str],
    db_path: str,
    qdrant_url: str,
    gateway_url: str,
    top_k: int = 12
) -> list[EvidenceChunk]:
    # BM25 via SQLite FTS5
    bm25_results = await bm25_search(query, tickers, filing_types, date_range, db_path)
    # Vector via Qdrant
    embedding = await embed_query(query, gateway_url)
    vector_results = await qdrant_search(embedding, tickers, filing_types, date_range, qdrant_url)
    # RRF
    merged = rrf_merge(bm25_results, vector_results)
    # Rerank
    reranked = await rerank(query, merged[:40], gateway_url)
    # Diversity
    diverse = apply_diversity_filter(reranked, max_per_section=3)
    return diverse[:top_k]
```

Test this function in isolation before wiring it into the graph. Use `pytest tests/test_retrieval.py -x`.

### 4c. Agent nodes

Build in this order (each depends on the previous):
1. `portfolio_context_planner.py` — depends on SQLite client + Gateway client
2. `filing_retrieval.py` — depends on retrieval module
3. `disclosure_change.py` — depends on Gateway client
4. `analyst_memo.py` — depends on Gateway client + risk scoring function

Each node function signature:
```python
async def {node_name}(state: AnalysisState) -> AnalysisState:
    try:
        # ... node logic ...
        return state.model_copy(update={...})
    except Exception as e:
        logger.error(f"{node_name} failed: {e}")
        return state.model_copy(update={"error": str(e), "partial": True})
```

### 4d. Graph wiring (`app/graph.py`)

```python
from langgraph.graph import StateGraph, END
from .agents import portfolio_context_planner, filing_retrieval, disclosure_change, analyst_memo
from packages.schemas.python.state import AnalysisState

def build_graph():
    builder = StateGraph(AnalysisState)
    builder.add_node("portfolio_context_planner", portfolio_context_planner)
    builder.add_node("filing_retrieval", filing_retrieval)
    builder.add_node("disclosure_change", disclosure_change)
    builder.add_node("analyst_memo", analyst_memo)
    builder.set_entry_point("portfolio_context_planner")
    builder.add_edge("portfolio_context_planner", "filing_retrieval")
    builder.add_edge("filing_retrieval", "disclosure_change")
    builder.add_edge("disclosure_change", "analyst_memo")
    builder.add_edge("analyst_memo", END)
    return builder.compile()

graph = build_graph()
```

Integration test (`tests/integration/test_graph.py`):
```python
async def test_full_graph_smoke():
    # Uses real Qdrant with pre-ingested data, mocked LLM calls
    state = AnalysisState(user_id="test", portfolio_id="p_test", question="What are supply chain risks?")
    result = await graph.ainvoke(state)
    assert result["memo"] is not None
    assert result["citation_pass_rate"] > 0.5
    assert "disclaimer" in result["memo"]["disclaimer"].lower()
```

---

## Step 5: Demo UI (`apps/demo-ui/`)

Build after Agent API is functional end-to-end.

```
apps/demo-ui/
  package.json      # Vite React scripts and dependencies
  src/
    App.jsx         # Main React app and tab composition
    lib/            # Browser Agent API client and runtime config
    data/           # Clearly labeled sample fallback data
  README.md         # HuggingFace Space description — AMD hardware story
```

HuggingFace Space metadata (in README.md YAML frontmatter):
```yaml
---
title: FinContext Agent
colorFrom: blue
colorTo: indigo
sdk: static
app_build_command: npm run build
app_file: dist/index.html
pinned: false
---
```

---

## Step 6: Evaluations (`packages/evals/`)

Build after the full pipeline is working. Run evals before the demo to verify quality.

```
packages/evals/
  eval_retrieval.py      # Retrieval recall against labeled query-document pairs
  eval_citations.py      # Citation precision: does each [citation_anchor] support the claim?
  eval_diff.py           # Disclosure diff quality: does classifier detect known real changes?
  eval_latency.py        # End-to-end latency benchmark across the 5 scenarios in amd-gpu-plan.md
  fixtures/
    labeled_queries.json  # 20 query + expected citations pairs for retrieval eval
    known_changes.json    # 10 known real AMD/NVDA disclosure changes for diff eval
```

Run all evals:
```bash
cd packages/evals
python eval_retrieval.py  # prints recall@20
python eval_citations.py  # prints citation precision
python eval_diff.py       # prints change detection accuracy
python eval_latency.py    # prints latency table (saves to benchmark_results.json)
```

The latency benchmark results feed the AMD benchmark panel in the React UI.
