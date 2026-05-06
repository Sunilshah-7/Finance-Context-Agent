# Architecture

## High-Level Flow

```text
User Portfolio
  -> Cloudflare Pages UI
  -> Cloudflare Worker API
  -> D1 metadata + R2 document storage + Queue jobs
  -> AMD GPU Agent API
  -> Ingestion, retrieval, multi-agent analysis, vLLM inference
  -> Findings, citations, scores
  -> Dashboard, memo, alerts
```

## Runtime Split

Cloudflare runs the user-facing and edge coordination layer:

- Static frontend on Pages.
- API gateway on Workers.
- R2 for uploaded portfolios, source PDFs, extracted markdown, and generated reports.
- D1 for users, portfolios, holdings, document metadata, job status, and audit records.
- Queues for ingestion and analysis jobs.
- Vectorize for demo-scale embeddings, or Postgres/pgvector for production.
- AI Gateway for request logging, caching, rate limits, and provider routing when calling model endpoints.

AMD Developer Cloud runs the GPU-heavy layer:

- vLLM OpenAI-compatible inference endpoint on ROCm.
- Embedding service for BGE/E5 models.
- Reranker service for cross-encoder ranking.
- FastAPI agent orchestration service.
- Batch workers for document parsing, chunking, extraction, summarization, and evals.

## Major Services

### Web App

- Framework: Next.js App Router with TypeScript.
- Deployment: Cloudflare Pages.
- Views:
  - Portfolio dashboard.
  - Filing explorer.
  - Disclosure diff viewer.
  - Risk score panel.
  - Analyst memo workspace.
  - Job status and source audit trail.

### Worker API

- Framework: Hono or lightweight TypeScript handlers.
- Deployment: Cloudflare Workers or Pages Functions.
- Responsibilities:
  - Authenticate requests.
  - Validate payloads.
  - Store uploads in R2.
  - Create D1 records.
  - Enqueue ingestion and analysis jobs.
  - Proxy safe model requests to AMD Agent API.
  - Enforce tenant, rate-limit, and request-size controls.

### Agent API

- Framework: FastAPI, LangGraph, Pydantic.
- Deployment: AMD Developer Cloud VM/container with ROCm-capable GPU nodes.
- Responsibilities:
  - Coordinate agents.
  - Call vLLM, embedding, and reranker services.
  - Read/write documents from R2 through signed URLs.
  - Persist analysis outputs.
  - Stream status and answer tokens back to the edge API.

### Ingestion Worker

- Language: Python.
- Responsibilities:
  - Fetch filings from SEC EDGAR.
  - Parse HTML filings and PDFs.
  - Normalize sections by filing type.
  - Extract tables and key metrics.
  - Chunk documents with stable citation anchors.
  - Generate embeddings.
  - Store chunks, metadata, and vector IDs.

### Retrieval Service

- Strategy: hybrid retrieval.
- First pass:
  - Metadata filters by ticker, filing type, date, section, portfolio holding.
  - BM25 keyword retrieval for exact accounting/risk terms.
  - Vector retrieval for semantic matches.
- Second pass:
  - Cross-encoder reranker.
  - Section-aware diversity selection.
  - Citation confidence scoring.

### Analysis Engine

- Pattern: multi-agent graph.
- Agents:
  - Portfolio Context Agent.
  - Filing Retrieval Agent.
  - Disclosure Change Agent.
  - Risk Scoring Agent.
  - Table and Metric Agent.
  - Analyst Memo Agent.
  - Citation Verifier Agent.
  - Compliance Guardrail Agent.

## Data Stores

| Store | Purpose | MVP Choice | Production Choice |
| --- | --- | --- | --- |
| D1 | app metadata, jobs, holdings | yes | Postgres acceptable |
| R2 | filings, PDFs, markdown, memos | yes | yes |
| Vectorize | demo vector index | yes | pgvector, Qdrant, Weaviate, or managed vector DB |
| KV | short-lived config/cache | optional | optional |
| Durable Objects | live job sessions, stream coordination | optional | useful for collaborative sessions |

## Request Lifecycle

1. User uploads portfolio CSV.
2. Worker validates and stores it in R2.
3. Worker creates portfolio and holding rows in D1.
4. Worker enqueues `portfolio.ingest`.
5. Agent API expands tickers into CIK/company metadata.
6. Ingestion worker fetches documents, parses, chunks, embeds, and indexes them.
7. User asks a question or requests a portfolio review.
8. Agent graph builds portfolio context, retrieves evidence, analyzes changes, scores risk, verifies citations, and returns a memo.
9. Worker persists results and streams them to the UI.

