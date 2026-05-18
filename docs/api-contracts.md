# API Contracts

All APIs are FastAPI services running behind the Agent API. The Gradio UI on HuggingFace Spaces communicates directly with the Agent API over HTTPS.

Authentication: all Agent API endpoints require `Authorization: Bearer {AGENT_API_KEY}` header.

---

## Agent API (port 8090)

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "ok",
  "inference_provider": "nvidia-nim",
  "reasoner": "ready",
  "planner": "ready",
  "qdrant": "ready",
  "chunks_indexed": 14392
}
```

### Upload Portfolio

```http
POST /api/portfolio/upload
Content-Type: multipart/form-data
Authorization: Bearer {AGENT_API_KEY}
```

Fields:
- `name` (string) — portfolio name
- `file` (file) — CSV with required columns: `ticker`, `shares`, `market_value`, optional: `sector`, `cost_basis`

CSV format example:
```csv
ticker,shares,market_value,sector,cost_basis
AMD,100,15000,Semiconductors,12000
MSFT,40,17000,Software,14000
JPM,50,10000,Financials,9000
TSLA,30,7500,Consumer Discretionary,8000
XOM,80,9500,Energy,8500
```

Response `200 OK`:
```json
{
  "portfolio_id": "p_abc123",
  "name": "Demo Portfolio",
  "holdings_count": 5,
  "total_value": 59000.0,
  "tickers": ["AMD", "MSFT", "JPM", "TSLA", "XOM"],
  "missing_cik": [],
  "status": "created"
}
```

Response `400 Bad Request` (missing columns):
```json
{
  "error": {
    "code": "invalid_csv",
    "message": "CSV is missing required columns: ['ticker', 'market_value']",
    "retryable": false,
    "request_id": "req_xyz789"
  }
}
```

### Start Portfolio Analysis

```http
POST /api/analyze
Content-Type: application/json
Authorization: Bearer {AGENT_API_KEY}
```

Request:
```json
{
  "portfolio_id": "p_abc123",
  "analysis_type": "latest_filings",
  "question": null
}
```

`analysis_type` values: `latest_filings` (default), `portfolio_review`, `custom_question`

If `analysis_type` is `custom_question`, `question` must be set.

Response `202 Accepted` (job is queued, runs async):
```json
{
  "job_id": "job_xyz789",
  "portfolio_id": "p_abc123",
  "status": "queued",
  "created_at": "2026-05-14T09:00:00Z"
}
```

### Get Job Status

```http
GET /api/jobs/{job_id}
Authorization: Bearer {AGENT_API_KEY}
```

Response:
```json
{
  "job_id": "job_xyz789",
  "portfolio_id": "p_abc123",
  "status": "running",
  "stage": "disclosure_change",
  "progress": 0.65,
  "created_at": "2026-05-14T09:00:00Z",
  "started_at": "2026-05-14T09:00:01Z",
  "completed_at": null,
  "error": null
}
```

`status` values: `queued`, `running`, `completed`, `failed`

`stage` values (in order): `planning`, `retrieving`, `analyzing`, `writing`, `complete`

When `status` is `completed`:
```json
{
  "job_id": "job_xyz789",
  "status": "completed",
  "stage": "complete",
  "progress": 1.0,
  "completed_at": "2026-05-14T09:01:32Z",
  "duration_seconds": 91,
  "citation_pass_rate": 0.94,
  "findings_count": 12
}
```

### Get Findings (Portfolio Analysis Results)

```http
GET /api/findings/{portfolio_id}?job_id={job_id}
Authorization: Bearer {AGENT_API_KEY}
```

`job_id` is optional. If omitted, returns findings from the most recent completed job.

Response:
```json
{
  "portfolio_id": "p_abc123",
  "job_id": "job_xyz789",
  "analyzed_at": "2026-05-14T09:01:32Z",
  "risk_scores": [
    {
      "ticker": "AMD",
      "overall_score": 58,
      "score_delta": 12,
      "confidence": 0.82,
      "drivers": [
        {
          "category": "supply_chain",
          "score": 70,
          "summary": "New language around third-party manufacturing dependency introduced in 2025 10-K.",
          "citation": "AMD 10-K Item 1A paragraph 42"
        }
      ],
      "portfolio_impact": {
        "holding_weight": 0.254,
        "sector_weight": 0.254,
        "exposure_level": "high"
      }
    }
  ],
  "memo": {
    "executive_summary": "Your semiconductor holdings face elevated supply-chain and export-control risk based on recent SEC disclosures.",
    "portfolio_exposure_affected": [
      {"ticker": "AMD", "weight": 0.254, "exposure_level": "high"},
      {"ticker": "NVDA", "weight": 0.212, "exposure_level": "high"}
    ],
    "top_disclosure_changes": [
      {
        "ticker": "AMD",
        "section": "Item 1A",
        "change_type": "new_risk",
        "materiality": "high",
        "summary": "2025 10-K introduces new disclosure on AI accelerator export restrictions.",
        "new_citation": "AMD 10-K Item 1A paragraph 18"
      }
    ],
    "evidence_table": [
      {
        "citation_id": "chunk_abc",
        "citation_anchor": "AMD 10-K Item 1A paragraph 42",
        "source_url": "https://www.sec.gov/Archives/edgar/data/2488/..."
      }
    ],
    "watchlist_questions": [
      "What percentage of AMD's AI accelerator revenue is currently subject to export restrictions?",
      "Has AMD diversified its primary TSMC manufacturing dependency since the 2024 10-K?"
    ],
    "limitations": "Analysis based on HTML EDGAR filings only. PDF exhibits and earnings transcripts not included in this analysis.",
    "confidence": 0.85,
    "disclaimer": "This memo is produced by an automated financial intelligence system for research purposes only..."
  }
}
```

### Disclosure Diff for a Ticker

```http
GET /api/diff/{ticker}?section=Item+1A&year_a=2023&year_b=2025&filing_type=10-K
Authorization: Bearer {AGENT_API_KEY}
```

Response:
```json
{
  "ticker": "AMD",
  "section": "Item 1A",
  "filing_type": "10-K",
  "year_a": "2023",
  "year_b": "2025",
  "changes": [
    {
      "change_type": "new_risk",
      "materiality": "high",
      "confidence": 0.91,
      "summary": "New risk disclosure around AI accelerator export controls added in 2025 filing.",
      "old_text": null,
      "new_text": "The U.S. government has implemented and may continue to implement export restrictions on advanced AI accelerators...",
      "old_citation_anchor": null,
      "new_citation_anchor": "AMD 10-K Item 1A paragraph 18",
      "old_source_url": null,
      "new_source_url": "https://www.sec.gov/Archives/edgar/data/2488/..."
    },
    {
      "change_type": "intensified_language",
      "materiality": "medium",
      "confidence": 0.78,
      "summary": "Supply chain dependency language strengthened from 'limited exposure' to 'concentration risk'.",
      "old_text": "We source certain components from a limited number of suppliers...",
      "new_text": "We have a significant concentration of supply chain dependency on certain third-party manufacturers...",
      "old_citation_anchor": "AMD 10-K Item 1A paragraph 42",
      "new_citation_anchor": "AMD 10-K Item 1A paragraph 51",
      "old_source_url": "https://www.sec.gov/Archives/edgar/data/2488/...",
      "new_source_url": "https://www.sec.gov/Archives/edgar/data/2488/..."
    }
  ]
}
```

### Citation-Backed Chat (Streaming)

```http
POST /api/chat
Content-Type: application/json
Authorization: Bearer {AGENT_API_KEY}
```

Request:
```json
{
  "portfolio_id": "p_abc123",
  "question": "What changed in supply-chain or customer concentration risk for my semiconductor holdings?"
}
```

Response: Server-Sent Events stream

```
data: {"type": "stage", "stage": "planning"}

data: {"type": "stage", "stage": "retrieving"}

data: {"type": "token", "text": "Your semiconductor"}
data: {"type": "token", "text": " holdings show"}
data: {"type": "token", "text": " elevated supply-chain"}
...

data: {"type": "citations", "citations": [
  {"citation_anchor": "AMD 10-K Item 1A paragraph 42", "chunk_id": "chunk_abc", "source_url": "..."}
]}

data: {"type": "done", "citation_pass_rate": 0.94}
```

### List Documents for a Ticker

```http
GET /api/documents/{ticker}
Authorization: Bearer {AGENT_API_KEY}
```

Response:
```json
{
  "ticker": "AMD",
  "documents": [
    {
      "document_id": "doc_xyz",
      "filing_type": "10-K",
      "filed_at": "2025-02-14",
      "accession_number": "0000002488-25-000012",
      "source_url": "https://www.sec.gov/Archives/edgar/data/2488/...",
      "sections_parsed": ["Item 1", "Item 1A", "Item 7", "Item 7A"],
      "chunks_indexed": 847
    }
  ]
}
```

### Benchmark Metrics

```http
GET /api/benchmark/metrics
Authorization: Bearer {AGENT_API_KEY}
```

Response:
```json
{
  "provider_info": {
    "provider": "nvidia-nim",
    "base_url": "https://integrate.api.nvidia.com/v1",
    "status": "ready"
  },
  "recent_requests": {
    "fincontext-reasoner": {
      "count": 12,
      "avg_input_tokens": 8420,
      "avg_output_tokens": 1850,
      "avg_time_to_first_token_ms": 380,
      "avg_total_latency_ms": 18240,
      "avg_tokens_per_second": 52.3
    },
    "fincontext-planner": {
      "count": 47,
      "avg_input_tokens": 2140,
      "avg_output_tokens": 320,
      "avg_time_to_first_token_ms": 120,
      "avg_total_latency_ms": 2850,
      "avg_tokens_per_second": 112.1
    },
    "embedding": {
      "count": 234,
      "avg_batch_size": 64,
      "avg_latency_ms": 85
    },
    "reranker": {
      "count": 89,
      "avg_candidates": 40,
      "avg_latency_ms": 210
    }
  },
  "benchmark_scenarios": {
    "single_10k_analysis_seconds": 32.4,
    "five_stock_portfolio_seconds": 91.2,
    "interactive_qa_seconds": 18.6
  }
}
```

---

## Inference Gateway API (port 8080)

Internal only. Not exposed externally. Agent API is the only caller.

### Chat Completions

```http
POST /v1/chat/completions
Content-Type: application/json
```

Passthrough of OpenAI chat completions format. The `model` field routes to the correct backend:
- `fincontext-reasoner` → NVIDIA NIM reasoner endpoint
- `fincontext-planner` → NVIDIA NIM planner endpoint

### Embeddings

```http
POST /v1/embeddings
Content-Type: application/json
```

Request:
```json
{"input": ["text 1", "text 2"], "model": "fincontext-embedding"}
```

Response follows OpenAI embeddings format. Routes to the configured embedding backend.

### Rerank

```http
POST /v1/rerank
Content-Type: application/json
```

Request:
```json
{
  "query": "supply chain risk third-party manufacturing",
  "documents": ["chunk text 1", "chunk text 2", ...],
  "top_n": 20
}
```

Response:
```json
{
  "results": [
    {"index": 0, "score": 0.94, "document": "chunk text 1"},
    {"index": 2, "score": 0.87, "document": "chunk text 3"},
    ...
  ]
}
```

Routes to the configured reranker backend.

### Health

```http
GET /health
```

Response:
```json
{
  "gateway": "ok",
  "reasoner": "ok",
  "planner": "ok",
  "embedding": "ok",
  "reranker": "ok"
}
```

---

## Standard Error Shape

All services use this error format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "retryable": true,
    "request_id": "req_xyz789"
  }
}
```

Standard error codes:
- `invalid_csv` — portfolio CSV validation failed
- `portfolio_not_found` — portfolio_id does not exist
- `job_not_found` — job_id does not exist
- `retrieval_insufficient` — not enough evidence found for the query
- `model_timeout` — LLM call exceeded 120 second timeout
- `qdrant_unavailable` — vector store connection failed
- `rate_limited` — too many concurrent requests (limit: 5)
