# API Contracts

`README.md` is the source of truth. These contracts describe the currently
implemented Go services.

## Agent API

Base URL in local Compose: `http://localhost:8090`

### `GET /api/health`

Returns service status, fixture mode, evidence count, dependency health, and the
research-assistance disclaimer marker.

Example:

```json
{
  "status": "degraded",
  "runtime": "go",
  "fixture_mode": true,
  "evidence": 5,
  "dependencies": {
    "sqlite": "ok",
    "qdrant": "ok",
    "gateway": "NIM_API_KEY is not configured"
  },
  "disclaimer": "research-assistance-only"
}
```

### `GET /api/demo/portfolio`

Returns the fixture portfolio.

Shape:

```json
{
  "id": "portfolio_demo",
  "name": "Demo Portfolio",
  "total_value": 100000,
  "holdings": [
    {
      "ticker": "AMD",
      "company": "Advanced Micro Devices, Inc.",
      "shares": 100,
      "market_value": 25000,
      "weight": 0.25,
      "sector": "Semiconductors"
    }
  ],
  "disclaimer": "This output is research assistance only and does not constitute investment advice."
}
```

### `POST /api/agent-runs`

Starts a fixture-backed agent run.

Request:

```json
{
  "question": "What changed in supply-chain or customer concentration risk for my semiconductor holdings?"
}
```

Response: `202 Accepted`

```json
{
  "id": "run_abc123",
  "status": "queued",
  "question": "...",
  "stages": [
    {
      "id": "portfolio_context",
      "label": "Portfolio context",
      "status": "queued"
    }
  ],
  "portfolio": {},
  "retrieved_evidence": [],
  "disclosure_changes": [],
  "risk_scores": [],
  "metrics": {},
  "created_at": "2026-06-16T12:00:00Z",
  "updated_at": "2026-06-16T12:00:00Z"
}
```

### `GET /api/agent-runs/{run_id}`

Returns the latest persisted or in-memory run state. Completed runs include:

- `retrieved_evidence`
- `disclosure_changes`
- `risk_scores`
- `memo`
- `metrics`

Run status values currently used:

- `queued`
- `running`
- `completed`
- `failed`

Stage ids currently used:

- `portfolio_context`
- `evidence_retrieval`
- `disclosure_diff`
- `risk_scoring`
- `memo_generation`

### `GET /api/agent-runs/{run_id}/events`

Server-Sent Events stream that emits repeated `event: run` messages until the
run is completed or failed.

### `GET /api/diff`

Returns fixture disclosure changes matching ticker, section, and year range.

Query parameters:

- `ticker`
- `section`
- `from`
- `to`

Example:

```http
GET /api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025
```

Response:

```json
{
  "changes": [
    {
      "id": "amd_supply_chain_2022_2025",
      "ticker": "AMD",
      "section": "Item 1A",
      "from_year": 2022,
      "to_year": 2025,
      "change_type": "intensified_language",
      "materiality": "high",
      "confidence": 0.91,
      "summary": "...",
      "old_text": "...",
      "new_text": "...",
      "citation_ids": ["amd_2025_supply_chain"]
    }
  ]
}
```

### `POST /api/chat`

Returns a fixture-backed citation-validated answer.

Request:

```json
{
  "question": "Why is AMD supply-chain risk higher this year?"
}
```

Response:

```json
{
  "answer": "...",
  "citations": [
    {
      "id": "amd_2025_supply_chain",
      "ticker": "AMD",
      "anchor": "AMD 10-K Item 1A paragraph 42",
      "filing_type": "10-K",
      "year": 2025,
      "section": "Item 1A",
      "excerpt": "...",
      "source_url": "https://www.sec.gov/..."
    }
  ],
  "disclaimer": "This output is research assistance only and does not constitute investment advice."
}
```

### `GET /api/metrics`

Returns fixture metrics used by the demo UI.

## Inference Gateway

Base URL in local Compose: `http://localhost:8080`

### `GET /health`

Returns provider name and upstream configuration state.

### `GET /metrics`

Returns request/error counters grouped by route label.

### `POST /v1/chat/completions`

OpenAI-compatible chat-completions proxy. The Gateway rewrites:

- `fincontext-planner` -> `NIM_PLANNER_MODEL`
- `fincontext-reasoner` -> `NIM_REASONER_MODEL`

Then it forwards to:

```text
{NIM_BASE_URL}/chat/completions
```

### `POST /v1/embeddings`

Passthrough proxy to:

```text
{EMBEDDING_URL}/v1/embeddings
```

Returns `503` when `EMBEDDING_URL` is not configured.

### `POST /v1/rerank`

Passthrough proxy to:

```text
{RERANKER_URL}/v1/rerank
```

Returns `503` when `RERANKER_URL` is not configured.

## Error Shape

Both Go services use this general error shape:

```json
{
  "error": {
    "code": "not_found",
    "message": "agent run not found",
    "retryable": false
  }
}
```

The richer request-id-bearing error contract remains target work.
