# Milestones

`README.md` is the source of truth. This milestone plan starts from the current
Go-first fixture-backed implementation.

## Completed

- Go Agent API boundary.
- Go Inference Gateway boundary.
- Next.js analyst console.
- Citation fixture validation.
- SQLite persistence for agent runs and seeded fixture metadata.
- Qdrant health check and collection initialization.
- Docker Compose stack.
- HuggingFace-ready root Dockerfile.
- Demo fixture data for portfolio, filings, evidence, disclosure changes, risk
  scores, memo, and metrics.

## Milestone 1: Stabilize Demo Runtime

- Keep `README.md`, `docs/architecture.md`, and service READMEs aligned.
- Verify `docker compose -f infra/docker-compose.yml --env-file .env up --build`.
- Verify `GET /api/health`, `GET /health`, and Qdrant health.
- Confirm the UI works when served by Agent API and when run separately with
  `NEXT_PUBLIC_API_BASE_URL`.

## Milestone 2: Gateway-Backed Retrieval Services

- Deploy/configure embedding backend.
- Deploy/configure reranker backend.
- Verify Gateway `/v1/embeddings` and `/v1/rerank`.
- Add request/error metrics that the UI can display beyond fixture metrics.

## Milestone 3: EDGAR Ingestion

- Fetch EDGAR HTML filings with a compliant `SEC_USER_AGENT`.
- Extract target filing sections.
- Chunk text with stable citation anchors.
- Write chunk text/metadata to SQLite.
- Write vectors/payloads to Qdrant.
- Produce a snapshot/backup process for demo data.

## Milestone 4: Live Retrieval

- Implement BM25 search over SQLite chunk text.
- Implement Qdrant vector search with payload filters.
- Merge candidates with reciprocal rank fusion.
- Rerank through Gateway.
- Apply section/ticker diversity.
- Return citation-ready evidence chunks.

## Milestone 5: Replace Fixture Run Path

- Preserve current Agent API response contracts.
- Swap curated evidence with retrieved evidence.
- Generate disclosure changes from retrieved filing pairs.
- Generate memo through Gateway reasoner.
- Keep citation validation/post-processing mandatory.

## Milestone 6: Public Demo Hardening

- Add public-demo-safe rate limiting.
- Decide auth boundary for admin/private endpoints.
- Keep Qdrant, Gateway, embedding, and reranker services private.
- Record final demo metrics.
- Freeze fixture/live data snapshots for rehearsal.
