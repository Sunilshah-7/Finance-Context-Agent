# API Contracts

## Cloudflare Worker API

### Upload Portfolio

```http
POST /api/portfolio/upload
Content-Type: multipart/form-data
```

Fields:

- `name`: portfolio name.
- `file`: CSV with ticker, shares, market_value, and optional sector/cost_basis.

Response:

```json
{
  "portfolio_id": "p_123",
  "holdings_count": 5,
  "status": "uploaded"
}
```

### Start Portfolio Analysis

```http
POST /api/analyze
Content-Type: application/json
```

Request:

```json
{
  "portfolio_id": "p_123",
  "analysis_type": "latest_filings",
  "tickers": ["AMD", "MSFT"],
  "filing_types": ["10-K", "10-Q"],
  "include_diff": true
}
```

Response:

```json
{
  "job_id": "job_123",
  "status": "queued"
}
```

### Job Status

```http
GET /api/jobs/job_123
```

Response:

```json
{
  "job_id": "job_123",
  "status": "running",
  "progress": 0.55,
  "stage": "citation_verification",
  "updated_at": "2026-05-06T12:00:00Z"
}
```

### Citation-Backed Chat

```http
POST /api/chat
Content-Type: application/json
```

Request:

```json
{
  "portfolio_id": "p_123",
  "question": "What changed in liquidity risk disclosures?",
  "tickers": ["AMD"]
}
```

Response:

```json
{
  "answer": "The latest filing shows...",
  "citations": [
    {
      "citation_id": "c_123",
      "label": "AMD 10-Q, Item 2, filed 2026-05-01, paragraph 18",
      "document_id": "doc_123",
      "chunk_id": "chunk_123"
    }
  ]
}
```

## AMD Agent API

### Analyze Portfolio

```http
POST /v1/portfolio/analyze
Authorization: Bearer <AMD_AGENT_API_KEY>
```

Request:

```json
{
  "job_id": "job_123",
  "portfolio_id": "p_123",
  "holdings": [
    {
      "ticker": "AMD",
      "market_value": 15000,
      "weight": 0.25
    }
  ],
  "analysis_type": "latest_filings",
  "r2_context": {
    "documents_bucket": "fincontext-documents",
    "reports_bucket": "fincontext-reports"
  }
}
```

Response:

```json
{
  "job_id": "job_123",
  "status": "accepted"
}
```

### Retrieve Evidence

```http
POST /v1/retrieve
Authorization: Bearer <AMD_AGENT_API_KEY>
```

Request:

```json
{
  "portfolio_id": "p_123",
  "query": "supply chain risk changes",
  "tickers": ["AMD"],
  "top_k": 12
}
```

Response:

```json
{
  "chunks": [
    {
      "chunk_id": "chunk_123",
      "document_id": "doc_123",
      "ticker": "AMD",
      "text": "...",
      "score": 0.91,
      "citation_anchor": "AMD 10-K Item 1A paragraph 42"
    }
  ]
}
```

### Generate Memo

```http
POST /v1/memo
Authorization: Bearer <AMD_AGENT_API_KEY>
```

Request:

```json
{
  "portfolio_id": "p_123",
  "job_id": "job_123",
  "format": "markdown"
}
```

Response:

```json
{
  "memo_r2_key": "reports/p_123/job_123/memo.md",
  "findings_count": 8,
  "citation_pass_rate": 0.95
}
```

## Error Shape

All services should return:

```json
{
  "error": {
    "code": "retrieval_low_confidence",
    "message": "Could not find enough citation-backed evidence.",
    "retryable": true,
    "request_id": "req_123"
  }
}
```

