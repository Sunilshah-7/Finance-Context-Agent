# AGENTS.md

Master context file for all AI coding agents (Claude Code, Codex, and any other agent) working on this repository. Read this before writing any code.

---

## What We Are Building

**FinContext Agent** is a multi-agent financial intelligence system for the AMD Developer Hackathon 2026 (Track 1: AI Agents & Agentic Workflows). It does three things that make it genuinely useful and technically impressive:

1. **Ingests SEC filings** from EDGAR (10-K annual reports, 10-Q quarterly reports) for a user's portfolio holdings and indexes them in a vector store with stable citation anchors.

2. **Detects disclosure language drift** — it finds where a company quietly changed how they described a risk, metric, or business condition between filings. For example: "we have no significant liquidity concerns" in the 2022 10-K becoming "we actively monitor our liquidity position given current market conditions" in the 2024 10-K. This is the hero demo feature.

3. **Produces citation-grounded portfolio impact memos** — not generic summaries, but analyst-style reports that say "your AMD holding has elevated supply-chain risk because Item 1A paragraph 42 of the 2025 10-K introduced new language around third-party manufacturing dependency that was absent in prior filings."

The AMD hardware angle: AMD MI300X has 192 GB of HBM3 VRAM. A 70B-parameter model in FP16 needs ~140 GB. A single MI300X can run it without multi-GPU orchestration. NVIDIA H100 (80 GB) cannot. Our demo shows a 70B model processing an entire annual report in one context window on a single GPU — that's the infrastructure story we're telling AMD judges.

---

## What We Are NOT Building

**Read this before adding any code or dependencies.**

| What NOT to build | Why |
|---|---|
| A separate edge/API platform | Adds cross-service wiring and auth for no MVP benefit |
| A JavaScript frontend | Gradio on HuggingFace Spaces is 10x faster to ship |
| 9 LangGraph agents | Requires 50+ hours of implementation, we have 9 days |
| Live demo ingestion | Never show a progress bar to judges, pre-load all data |
| PDF parsing for MVP | EDGAR HTML is parseable and reliable; PDF is a trap |
| Real-time market data | Out of scope, adds cost and API dependencies |
| Buy/sell/hold recommendations | Legal non-goal, compliance requirement |
| Broker integrations | Out of scope for hackathon |

The frontend is `apps/demo-ui/` (Gradio). Do not add a separate web app unless the MVP is already complete.

---

## Technology Stack and Rationale

### Compute: AMD Developer Cloud

One VM with AMD Instinct GPU (ideally MI300X or MI250). All services run on this machine. No separate compute node needed.

Why: The $100 credit gives ~50 hours of GPU time. Everything on one machine eliminates cross-cloud networking latency, secrets management complexity, and inter-service authentication overhead. Localhost calls are sub-millisecond.

### LLM Serving: vLLM with ROCm backend

vLLM provides an OpenAI-compatible API (`/v1/chat/completions`, `/v1/embeddings`) and is the standard choice for serving open-source LLMs on AMD GPUs via ROCm. It handles continuous batching, KV cache management, and speculative decoding automatically.

Run two instances:
- Port 8000: `Qwen/Qwen2.5-72B-Instruct` — used only for final memo generation
- Port 8001: `Qwen/Qwen2.5-14B-Instruct` — used for retrieval planning, diff classification, and any intermediate LLM calls

Why Qwen2.5 over Llama 3: Qwen2.5 has strong instruction-following on structured output tasks. The 72B variant benchmarks competitively with GPT-4o on coding and reasoning. The 14B variant is fast enough for sub-second intermediate calls.

### Embeddings and Reranking: HuggingFace TEI (Text Embeddings Inference)

TEI is HuggingFace's optimized embedding and reranking server. It serves BAAI/bge-large-en-v1.5 (1024-dimensional embeddings) and BAAI/bge-reranker-large with hardware-aware batching on AMD ROCm.

Why BGE over other embedding models: BGE-large-en-v1.5 consistently ranks at the top of the MTEB retrieval benchmark for its size class. The BGE reranker (cross-encoder) significantly improves precision over bi-encoder-only retrieval on domain-specific text.

### Vector Store: Qdrant

Qdrant runs in Docker on the AMD VM. It provides:
- HNSW approximate nearest-neighbor search
- Rich payload filtering (exact match, range, geo) without a separate SQL query
- Named collections with configurable distance metrics
- REST and gRPC APIs
- Persistent storage via Docker volume
- Snapshot export for sharing pre-ingested demo data between teammates

Why Qdrant: it lets us do `ticker = "AMD" AND filing_type IN ["10-K", "10-Q"] AND filed_at >= "2023-01-01"` as a single query with vector search, while also supporting snapshots for sharing pre-ingested demo data.

Why Qdrant over Chroma: Qdrant has better documentation, a stable REST API, and production-grade performance. Chroma is fine for prototypes but Qdrant is easier to operate in a shared team environment.

### Metadata: SQLite

SQLite stores portfolios, holdings, documents, chunk metadata, analysis jobs, and findings. No setup required. WAL mode handles concurrent reads from multiple processes.

Why SQLite over Postgres: Zero setup, file-based backup, trivially snapshotted. Postgres adds Docker complexity for zero benefit at hackathon scale. If the project goes beyond MVP, swap to Postgres using the same schema.

### Agent Orchestration: LangGraph

LangGraph provides typed shared state, conditional graph edges, built-in retry logic, and structured I/O for multi-agent workflows. The graph has 4 nodes in a fixed linear sequence (no branching in MVP).

Why LangGraph over raw LangChain: LangChain's agent loop is opaque and hard to debug. LangGraph makes the state transitions explicit and testable. Each node is a pure function that takes state and returns updated state — easy to unit test in isolation.

Why LangGraph over AutoGen or CrewAI: LangGraph is lower-level and gives more control over exactly what each agent does and sees. CrewAI and AutoGen are higher-level but abstract away too much for a demo where we need to control every output for citation accuracy.

### API Framework: FastAPI

FastAPI is used for both the Agent API and the Inference Gateway. It provides:
- Automatic OpenAPI documentation (useful for debugging during hackathon)
- Pydantic integration for request/response validation
- Async support for concurrent model calls
- SSE (Server-Sent Events) for streaming memo generation to the Gradio UI

### Demo UI: Gradio on HuggingFace Spaces

Gradio is HuggingFace's UI framework. A Gradio app deployed to HuggingFace Spaces:
- Satisfies the hackathon's HuggingFace integration requirement
- Is publicly accessible for judges without any auth setup
- Deploys with a single `git push`
- Takes 2 hours to build, not 2 days like a custom JavaScript frontend
- Supports SSE streaming for live memo generation

---

## The 4-Agent LangGraph Graph

### Node 1: portfolio_context_planner

**Input state fields consumed:** `user_id`, `portfolio_id`, `question`

**What it does:**
1. Loads holdings from SQLite for the given portfolio
2. Computes sector exposure and weight distribution
3. If a specific question was asked, identifies which tickers are most relevant
4. Translates the user question (or portfolio review request) into specific retrieval instructions: filing types to search, sections to prioritize, date ranges to compare, keywords to anchor BM25 search
5. Identifies the top 3–5 holdings by exposure weight for prioritization

**Output state fields set:** `holdings`, `target_tickers`, `retrieval_plan`

**Model used:** Qwen2.5-14B (structured output for the retrieval plan)

**What it must NOT do:** Retrieve any documents. It only plans retrieval.

### Node 2: filing_retrieval

**Input state fields consumed:** `retrieval_plan`, `target_tickers`

**What it does:**
1. For each ticker in `target_tickers`, runs parallel retrieval:
   - BM25 search on SQLite FTS5 using the query text and financial keywords from the retrieval plan
   - Vector search on Qdrant with payload filter `ticker=X AND filing_type IN [...] AND filed_at IN [range]`
2. Merges BM25 and vector results using Reciprocal Rank Fusion (k=60)
3. Sends merged candidates to BGE reranker (Inference Gateway, port 8003)
4. Applies section diversity: max 3 chunks per section per ticker
5. Returns top 12 chunks total across all tickers (not 12 per ticker)

**Output state fields set:** `retrieved_chunks`

**Model used:** No LLM. Pure retrieval + BGE reranker.

**What it must NOT do:** Generate any claims or summaries. Only return raw evidence chunks with citation anchors.

### Node 3: disclosure_change

**Input state fields consumed:** `retrieved_chunks`, `target_tickers`, `retrieval_plan`

**What it does:**
1. Groups retrieved chunks by ticker, section, and filing date
2. Finds same-section chunks from different filing dates (e.g., Item 1A from 2023-10-K vs 2024-10-K)
3. Normalizes boilerplate (page headers, XBRL tags, legal disclaimers) from both versions
4. For each section pair, asks Qwen2.5-14B to classify the change type:
   - `new_risk` — new risk factor or disclosure that did not exist before
   - `removed_risk` — prior risk factor or disclosure removed
   - `intensified_language` — same risk, but described with stronger language
   - `softened_language` — same risk, but described with weaker or hedged language
   - `metric_changed` — numerical value changed (revenue, margins, guidance)
   - `legal_accounting_update` — change driven by regulation or accounting standard
   - `boilerplate` — no material change in substance
5. Discards `boilerplate` classifications — they are not passed to the memo node
6. Records old_citation_anchor and new_citation_anchor for every non-boilerplate change

**Output state fields set:** `disclosure_changes`

**Model used:** Qwen2.5-14B (structured output for classification)

**Risk-bearing language signals to watch for:** "may", "could", "materially", "adversely", "substantial", "uncertain", "depends", "concentration", "liquidity", "impairment", "going concern". These raise flags but only increase severity when supported by evidence — never based on language alone.

### Node 4: analyst_memo

**Input state fields consumed:** `holdings`, `retrieved_chunks`, `disclosure_changes`, `question`

**What it does:**
1. Computes a risk score per holding using the formula in `docs/risk-scoring.md`
2. Drafts a structured analyst memo with Qwen2.5-72B in this exact structure:
   - Executive Summary (2–3 sentences)
   - Portfolio Exposure Affected (table: ticker, weight, exposure level)
   - Top Disclosure Changes (one paragraph per change, with citation)
   - Risk Score Changes (table: ticker, score, delta, top driver)
   - Evidence Table (all citations used)
   - Watchlist Questions for next earnings call
   - Limitations and Confidence
   - Investment Research Disclaimer (required, hardcoded)
3. Post-processes output: every `[citation_id]` in the generated text is verified against `retrieved_chunks`. Sentences with unverified citations are removed.
4. Computes overall citation pass rate and adds it to state

**Output state fields set:** `memo`, `risk_scores`, `citation_pass_rate`

**Model used:** Qwen2.5-72B (quality matters for judge-facing output)

**What it must NOT do:** Generate any claims that are not traceable to a retrieved chunk. The post-processing step enforces this, but the prompt should also instruct the model to only cite chunks it has seen.

---

## Shared State Schema

```python
class AnalysisState(BaseModel):
    # Input
    user_id: str
    portfolio_id: str
    question: str | None

    # After node 1
    holdings: list[Holding] = []
    target_tickers: list[str] = []
    retrieval_plan: RetrievalPlan | None = None

    # After node 2
    retrieved_chunks: list[EvidenceChunk] = []

    # After node 3
    disclosure_changes: list[DisclosureChange] = []

    # After node 4
    risk_scores: list[RiskScore] = []
    memo: AnalystMemo | None = None
    citation_pass_rate: float | None = None

    # Error handling
    error: str | None = None
    partial: bool = False
```

All schema types are defined in `packages/schemas/python/`. Never define schema types inline in service code — always import from the shared schemas package.

---

## Data Pipeline

### SEC EDGAR Ingestion

EDGAR provides a free, rate-limited REST API. All ingestion uses direct EDGAR endpoints (no third-party API subscriptions needed).

Key EDGAR endpoints:
- `https://data.sec.gov/submissions/CIK{cik_padded}.json` — company metadata and filing list
- `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}/{doc}` — actual filing document

Rate limit: 10 requests per second. Must set `User-Agent` header to `FinContextAgent/0.1 your-email@example.com` or requests are blocked.

Ticker-to-CIK mapping: `https://www.sec.gov/files/company_tickers.json` — download once and cache.

### HTML Parsing

EDGAR HTML filings have consistent structure. Section boundaries are marked by `<div>` or `<p>` elements containing the item label text (`Item 1A`, `Item 7`, etc.). Use BeautifulSoup4 + lxml.

Key filing sections to extract:
- Item 1: Business
- Item 1A: Risk Factors
- Item 7: Management's Discussion and Analysis
- Item 7A: Quantitative Disclosures About Market Risk
- Item 8: Financial Statements (tables only for MVP)

Do NOT attempt PDF parsing for MVP. EDGAR HTML is available for all modern filings and is far more reliably parseable.

### Chunking Rules

- Target chunk size: 600–1,000 tokens
- Overlap: 100 tokens between consecutive chunks
- Never split a table row across chunks
- Preserve section hierarchy in chunk metadata: `section="Item 1A"`, `item_label="Risk Factors"`
- Assign `chunk_index` (0-based) within the document for stable ordering
- Compute `citation_anchor` at chunk creation time: `f"{ticker} {filing_type} {section_label} paragraph {paragraph_index}"`
- Store `text_hash` (SHA256 of chunk text) for deduplication

### Qdrant Schema

Collection name: `fincontext_chunks` (do not change this — the retrieval service is hardcoded to this name).

Vector dimensions: 1024 (BGE-large-en-v1.5 output dimension).

Required payload fields per chunk:
```json
{
  "chunk_id": "string (UUID)",
  "document_id": "string",
  "ticker": "string (e.g. AMD)",
  "cik": "string",
  "filing_type": "string (e.g. 10-K)",
  "filed_at": "string (ISO date, e.g. 2025-02-14)",
  "fiscal_period": "string (e.g. FY2024, Q3-2024)",
  "section": "string (e.g. Item 1A)",
  "item_label": "string (e.g. Risk Factors)",
  "chunk_index": "integer",
  "token_count": "integer",
  "text_hash": "string",
  "citation_anchor": "string",
  "source_url": "string (SEC EDGAR URL)"
}
```

### SQLite Schema

Located at `infra/schema.sql`. Apply with:
```bash
sqlite3 fincontext.db < infra/schema.sql
```

Tables: `portfolios`, `holdings`, `documents`, `chunks`, `analysis_jobs`, `findings`.

The `chunks` table stores chunk metadata for BM25 search (FTS5 virtual table on `text` column). The actual chunk text is stored in SQLite for BM25; the vector is stored in Qdrant. The `vector_id` field in the `chunks` table is the Qdrant point ID linking the two.

---

## Retrieval Implementation Details

### BM25 with SQLite FTS5

```sql
CREATE VIRTUAL TABLE chunks_fts USING fts5(
  text,
  ticker UNINDEXED,
  filing_type UNINDEXED,
  filed_at UNINDEXED,
  citation_anchor UNINDEXED,
  content='chunks',
  content_rowid='rowid'
);
```

Query:
```sql
SELECT c.*, bm25(chunks_fts) AS bm25_score
FROM chunks_fts
JOIN chunks c ON c.rowid = chunks_fts.rowid
WHERE chunks_fts MATCH :query
  AND ticker = :ticker
  AND filing_type IN (:filing_types)
ORDER BY bm25_score
LIMIT 50;
```

### Reciprocal Rank Fusion

```python
def rrf(bm25_results, vector_results, k=60):
    scores = {}
    for rank, chunk in enumerate(bm25_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1 / (k + rank + 1)
    for rank, chunk in enumerate(vector_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Reranker Call

POST to Inference Gateway at `/v1/rerank`:
```json
{
  "query": "supply chain risk third-party manufacturing",
  "documents": ["chunk_text_1", "chunk_text_2", ...],
  "top_n": 20
}
```

Response includes scores. Re-sort the merged candidates by reranker score before applying the section diversity filter.

---

## Inference Gateway Contract

All LLM, embedding, and reranker calls from the Agent API go through the Inference Gateway at `http://localhost:8080`. The gateway routes based on endpoint:

| Endpoint | Routes to | Port |
|----------|-----------|------|
| POST /v1/chat/completions (model=fincontext-planner) | vLLM 14B | 8001 |
| POST /v1/chat/completions (model=fincontext-reasoner) | vLLM 72B | 8000 |
| POST /v1/embeddings | TEI embedding service | 8002 |
| POST /v1/rerank | TEI reranker service | 8003 |
| GET /health | all services | — |
| GET /metrics | Prometheus metrics | — |

The gateway adds request IDs, logs latency, and normalizes error responses. Agent API code never calls vLLM or TEI directly — always through the gateway.

---

## Coding Conventions

### Python

- Python 3.12
- All Pydantic models in `packages/schemas/python/` — never define schema types inline in service code
- Use `httpx.AsyncClient` for all outgoing HTTP calls (not `requests`)
- Use `asyncio.gather` for parallel model calls (e.g., embedding multiple chunks simultaneously)
- Type annotations required on all function signatures
- No `print()` for logging — use Python's `logging` module with structured JSON format
- All agent nodes are pure functions: `(state: AnalysisState) -> AnalysisState`

### Tests

- Every LangGraph node must have a unit test that mocks the Inference Gateway
- The retrieval pipeline must have an integration test against a local Qdrant instance
- Test files live in `tests/` within each service directory
- Run with `pytest tests/ -x` — `-x` stops on first failure

### API responses

- All FastAPI endpoints return Pydantic models, never raw dicts
- Error responses always include `{"error": {"code": str, "message": str, "retryable": bool, "request_id": str}}`
- Streaming endpoints use SSE (Server-Sent Events) via FastAPI's `StreamingResponse`

---

## Workload Division for AI Agents

When multiple agents (Claude Code and Codex) are working in parallel, use this division to avoid conflicts:

**Claude Code works on:**
- `services/agent-api/` — LangGraph graph, agent nodes, FastAPI endpoints
- `packages/schemas/` — Pydantic state models and shared types
- `packages/evals/` — evaluation scripts

**Codex works on:**
- `services/ingestion-worker/` — SEC EDGAR client, HTML parser, chunking, embedding pipeline
- `services/inference-gateway/` — FastAPI proxy service
- `apps/demo-ui/` — Gradio interface
- `infra/` — Docker Compose configuration, SQLite schema

Both agents should coordinate on `packages/schemas/python/state.py` — this is the shared contract. Any change to `AnalysisState` must be discussed before implementation, as it affects both service teams.

---

## AMD Hardware Demo Script

This is what we show to judges (in order):

1. **Upload the seed portfolio CSV** (`/demo/seed_portfolio.csv`) — AMD, NVDA, MSFT, JPM, TSLA
2. **Trigger portfolio analysis** — the 4-agent graph runs, pre-ingested data is already in Qdrant
3. **Show the disclosure diff for AMD** — side-by-side comparison of Item 1A risk factor language across 2022–2025 10-Ks, with classified changes highlighted
4. **Ask a question:** "What changed in supply-chain or customer concentration risk for my semiconductor holdings?"
5. **Show the analyst memo** — citation-grounded, with inline `[citation_anchor]` references linking to the exact filing paragraph
6. **Show the AMD GPU benchmark panel** — tokens/sec, time-to-first-token, concurrent requests, GPU memory utilization
7. **Explain the hardware angle:** "This 72B parameter model runs in FP16 on a single AMD MI300X because it has 192 GB of VRAM. On NVIDIA H100 (80 GB), this same model requires multi-GPU orchestration with tensor parallelism. We use the full long-context window — 65,536 tokens — to analyze an entire 10-K in a single pass."

---

## HuggingFace Integration Checklist

The hackathon requires meaningful HuggingFace integration. We satisfy this through:

- [ ] Models pulled from HuggingFace Hub: `Qwen/Qwen2.5-72B-Instruct`, `Qwen/Qwen2.5-14B-Instruct`, `BAAI/bge-large-en-v1.5`, `BAAI/bge-reranker-large`
- [ ] `HF_TOKEN` environment variable used for authenticated model downloads
- [ ] Demo UI deployed as a public HuggingFace Space
- [ ] Space README explains what AMD hardware is being used and links to the AMD Developer Cloud
- [ ] Build-in-Public posts tagged `#AMDDevHackathon` and `#HuggingFace` on X/LinkedIn

---

## Build-in-Public Requirement

The hackathon has a dedicated prize pool for teams that post 3+ technical build-in-public posts on X or LinkedIn tagged `#AMDDevHackathon`. Post about:

1. Getting vLLM running on ROCm — what flags worked, what didn't
2. Hybrid BM25 + vector retrieval quality comparison on financial text
3. The AMD MI300X 192 GB VRAM advantage for 70B model inference — real benchmark numbers

These posts also make your submission visible to judges before they open it.

---

## Git Workflow

### Branch Strategy

Never commit directly to `main`. Always work on a feature branch.

| Prefix | When to use | Example |
|--------|-------------|---------|
| `feat/` | New working feature or service | `feat/ingestion-worker` |
| `feat/` | New agent node implementation | `feat/disclosure-change-agent` |
| `fix/` | Bug fix in any service | `fix/qdrant-filter-query` |
| `docs/` | Documentation-only changes | `docs/update-api-contracts` |
| `infra/` | Docker Compose, schema, deployment config | `infra/add-qdrant-compose` |
| `eval/` | Evaluation scripts and fixtures | `eval/retrieval-recall-suite` |

### Commit Message Format

```
<type>(<scope>): <short description>

<optional body: what and why, not how>
```

Types: `feat`, `fix`, `docs`, `infra`, `test`, `refactor`, `chore`

Scope (optional but recommended): `agent-api`, `ingestion`, `gateway`, `demo-ui`, `schemas`, `evals`, `infra`

Examples:
```
feat(agent-api): implement portfolio_context_planner node with Qwen2.5-14B
feat(ingestion): add EDGAR HTML section extractor with BeautifulSoup
fix(retrieval): correct RRF merge to handle duplicate chunk IDs
docs(agent-design): add citation post-processing implementation detail
infra: add Qdrant and TEI services to Docker Compose
test(agent-api): add unit tests for all 4 LangGraph nodes
```

### Commit Granularity

Each commit should represent one logical unit of work that compiles/passes basic tests. Do not batch unrelated changes into one commit. Do not split one logical change across many commits.

Good commit granularity examples:
- Implement one complete agent node = one commit
- Implement the EDGAR client = one commit
- Fix one specific bug = one commit
- Update all READMEs after an architecture decision = one commit

### Pull Request Process

1. Branch off `main`: `git checkout -b feat/your-feature`
2. Make commits as you work (frequent small commits are fine on a feature branch)
3. Before opening a PR, squash or clean up commits to logical units
4. PR title should match the primary commit message format
5. PR body should describe what the PR does and link to any relevant docs

### AI Agent Branch Assignment

To avoid conflicts when Claude Code and Codex are both working:

- **Claude Code** works on: `feat/agent-api-*`, `feat/schemas-*`, `test/agent-api-*`
- **Codex** works on: `feat/ingestion-*`, `feat/inference-gateway-*`, `feat/demo-ui-*`, `infra/*`

If either agent needs to touch a file owned by the other, stop and coordinate first.

### Never do these

- Force push to `main`
- Merge your own PR without teammate review (on feature branches that affect both services)
- Commit `.env` files, API keys, or `fincontext.db`
- Commit the Qdrant data volume or model cache directory

`.gitignore` must include:
```
.env
fincontext.db
fincontext_demo.db
/models/
qdrant_storage/
__pycache__/
.venv/
*.pyc
```

---

## Environment Variables Reference

```bash
# AMD VM
AMD_VM_PUBLIC_IP=            # public IP of the AMD Developer Cloud VM

# Model services (all localhost from AMD VM perspective)
VLLM_REASONER_URL=http://localhost:8000/v1   # Qwen2.5-72B
VLLM_PLANNER_URL=http://localhost:8001/v1    # Qwen2.5-14B
EMBEDDING_URL=http://localhost:8002          # BGE embedding
RERANKER_URL=http://localhost:8003           # BGE reranker
INFERENCE_GATEWAY_URL=http://localhost:8080  # unified gateway
AGENT_API_URL=http://localhost:8090          # LangGraph agent service

# Vector and metadata storage
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=fincontext_chunks
SQLITE_DB_PATH=./fincontext.db

# HuggingFace
HF_TOKEN=                    # for authenticated model downloads from HF Hub
HF_HOME=/models/huggingface  # model cache directory on AMD VM

# SEC EDGAR (required, no key needed)
SEC_USER_AGENT=FinContextAgent/0.1 your-email@example.com

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
```
