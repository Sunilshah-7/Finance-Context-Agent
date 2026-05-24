# TODO

Task plan for completing FinContext Agent with three engineers: Sunil, Abhiyan, and Kishan.

This plan follows `AGENTS.md` as the source of truth. Build the current architecture: a lightweight backend running FastAPI, LangGraph, Qdrant, and SQLite, NVIDIA NIM for hosted chat completions, and a public React demo on HuggingFace Static Spaces.

Do not build a separate edge/API platform or second frontend. The project uses the Agent API backend and the React app in `apps/demo-ui/`.

## Task Types

- **Atomic task:** Independent task one engineer can complete without blocking another engineer.
- **Collaboration task:** Requires two or more engineers to agree on schema, API behavior, prompts, data shape, or demo expectations.
- **Integration task:** Final assembly or verification across multiple components.

## Task Ownership Summary

| Engineer | Primary Ownership |
| --- | --- |
| Sunil | Backend infrastructure, schema, Agent API skeleton, deployment, final submission |
| Abhiyan | EDGAR ingestion, parsing, chunking, embeddings, Qdrant/SQLite indexing, retrieval quality |
| Kishan | Inference Gateway, LangGraph nodes, React UI, benchmark panel, demo polish |

## Shared Rules

- [x] Work on feature branches; never commit directly to `main` or `dev`. All PRs target `dev`.
- [x] Do not commit `.env`, `fincontext.db`, Qdrant storage, model cache, or secrets.
- [x] Use Python 3.12 and Pydantic models from `packages/schemas/python/`.
- [x] Every service-to-service model call must go through the Inference Gateway on port `8080`.
- [x] Use the NIM planner model for planner/diff calls and the NIM reasoner model only for final memo generation.
- [x] Every factual memo claim must have a valid citation mapped to a retrieved chunk.
- [x] Never generate buy/sell/hold/short recommendations.
- [ ] Pre-ingest demo data before the live demo; do not demo live EDGAR ingestion.

---

# Tasks for Sunil

## Atomic Tasks

- [x] Create or verify `.gitignore` includes `.env`, `fincontext.db`, `fincontext_demo.db`, `/models/`, `qdrant_storage/`, `__pycache__/`, `.venv/`, and `*.pyc`.
- [x] Create `configs/.env.example` for the current architecture with Agent API, Gateway, NIM, retrieval backends, Qdrant, SQLite, SEC EDGAR, and logging settings.
- [x] Create `infra/schema.sql` for SQLite tables: `portfolios`, `holdings`, `documents`, `chunks`, `chunks_fts`, `analysis_jobs`, and `findings`.
- [x] Add FTS5 triggers in `infra/schema.sql` so inserts into `chunks` populate `chunks_fts`.
- [x] Create Docker Compose support for local services, including Qdrant.
- [x] Add Qdrant collection initialization script for `fincontext_chunks` with 1024 dimensions and payload indexes for `ticker`, `filing_type`, `filed_at`, and `section`.
- [ ] Provision backend host with Ubuntu, Docker, enough disk for Qdrant data, SQLite, and EDGAR cache.
- [ ] Configure NVIDIA NIM credentials and verify hosted chat completions through the Gateway.
- [ ] Start storage/retrieval services and verify Qdrant and Gateway health.
- [x] Create `packages/schemas/python/state.py` with `AnalysisState`, `Holding`, `RetrievalPlan`, `EvidenceChunk`, `DisclosureChange`, `RiskScore`, `Citation`, and `AnalystMemo`.
- [x] Create `packages/schemas/python/db.py` for SQLite row models.
- [x] Create `packages/schemas/python/api.py` for FastAPI request/response models from `docs/api-contracts.md`.
- [x] Add `packages/schemas` packaging files so services can install it with `pip install -e ../../packages/schemas`.
- [x] Create `services/agent-api/main.py` with FastAPI app and `GET /health`.
- [x] Verify `services/agent-api` local Python 3.12 test environment can install `requirements.txt` and import `fincontext_schemas`.
- [x] Add `services/agent-api/tests/__init__.py` so tests can import shared fixtures such as `tests.test_nodes.sample_chunk`.
- [x] Implement Agent API bearer-token authentication using `AGENT_API_KEY` (optional; no-op when key is empty).
- [x] Implement `POST /api/portfolio/upload` to parse CSV, validate required columns, resolve basic portfolio totals, and write portfolio/holdings rows.
- [x] Implement `POST /api/analyze` job creation with async background-task.
- [x] Implement `GET /api/jobs/{job_id}` to read job status from SQLite.
- [x] Implement Agent API SQLite client functions for portfolios, holdings, documents, chunks, jobs, findings, and results cache.
- [x] Add Agent API node unit tests (test_nodes.py) and retrieval unit test (test_retrieval.py).
- [ ] Configure firewall/reverse proxy so only Agent API port `8090` is externally reachable.
- [ ] Set up HTTPS for Agent API with nginx or a tested tunnel fallback.
- [x] Create Qdrant snapshot and SQLite backup commands in an ops note or script.
- [x] Update root README with final architecture and local setup commands.

## Collaboration Tasks

- [x] With Abhiyan: finalize SQLite `documents` and `chunks` columns before ingestion writes data.
- [x] With Abhiyan: verify `citation_anchor` format exactly matches `{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}` or table equivalent.
- [x] With Kishan: finalize Agent API response schemas for React tabs before UI wiring.
- [x] With Kishan: agree on job stages and progress values: `planning`, `retrieving`, `analyzing`, `writing`, `complete`.
- [x] With Abhiyan and Kishan: review `AnalysisState` before any agent node implementation starts.
- [ ] With Abhiyan and Kishan: define demo seed portfolio and confirm all tickers are pre-ingested.

## Integration Tasks

- [ ] Apply `infra/schema.sql` to create `fincontext.db` on the backend host.
- [ ] Start full backend host stack and publish service health checklist.
- [ ] Restore or verify Qdrant and SQLite demo snapshots on the backend host.
- [ ] Run end-to-end smoke test: upload portfolio → create job → graph starts → job completes.
- [ ] Verify HuggingFace Space can reach Agent API over HTTPS with public demo-safe CORS/rate limits.
- [ ] Run final security check: no secrets committed, only required port exposed, disclaimer always present.
- [ ] Prepare final lablab.ai submission: project description, architecture, NVIDIA NIM inference story, HuggingFace integration, GitHub repo, demo video, and Space URL.

---

# Tasks for Abhiyan

## Atomic Tasks

- [x] Create `services/ingestion-worker/requirements.txt` with `httpx`, `beautifulsoup4`, `lxml`, `tiktoken`, `qdrant-client`, `pydantic`, and `pytest`.
- [x] Implement `worker/models.py` for `FilingRef`, `NormalizedDocument`, `NormalizedSection`, `ChunkInput`, and `ChunkWithEmbedding`.
- [x] Implement `worker/sec_client.py` with async EDGAR client, required `SEC_USER_AGENT`, ticker-to-CIK cache, submissions fetch, filing filtering, and document download.
- [x] Add SEC rate limiter capped at 10 requests per second with polite delay for document downloads.
- [x] Add local EDGAR HTML cache to avoid repeated downloads during development.
- [x] Write `test_sec_client.py` verifying ticker-to-CIK resolution with a known SEC company fixture.
- [x] Implement `worker/parsers/sec_html.py` using BeautifulSoup/lxml to extract `Item 1`, `Item 1A`, `Item 7`, `Item 7A`, and `Item 8`.
- [x] Normalize EDGAR HTML by removing XBRL tags, table-of-contents noise, headers, and repeated whitespace.
- [x] Add SEC-like 10-K parser fixture that exercises realistic `Item 1A` structure without committing a full filing.
- [x] Write parser test verifying `Item 1A` extracts at least 1000 words.
- [x] Implement `worker/chunking.py` with paragraph-aware 600-1000 token chunks, 100-token overlap, max 1200 tokens, and min 200 tokens.
- [x] Ensure tables become standalone chunks and are not split.
- [x] Generate stable `citation_anchor`, `chunk_index`, `token_count`, `text_hash`, and `is_table` fields.
- [x] Write chunking tests for size bounds, overlap, table handling, and citation format.
- [x] Implement `worker/embeddings.py` to call Inference Gateway `/v1/embeddings` in batches up to 256 texts.
- [x] Add retries with exponential backoff for embedding failures.
- [x] Write embedding shape test expecting 1024-dimensional vectors.
- [x] Implement `worker/db.py` to upsert documents and chunks into SQLite.
- [x] Implement `worker/vector_store.py` to upsert chunk vectors and payload metadata into Qdrant.
- [x] Add duplicate skip logic using `text_hash`.
- [x] Implement `ingest.py` CLI with arguments for tickers, filing types, years, DB path, Qdrant URL, and Gateway URL.
- [x] Add SQLite FTS validation helper for checking searchable chunk rows.
- [x] Add Qdrant point-count validation helper for comparing indexed vectors with SQLite chunks.
- [x] Add citation anchor inspection helper for paragraph/table anchor format checks.
- [x] Add ingested document summary helper for ticker, filing type, filed date, parsed sections, and chunk counts.
- [x] Add NIM Gateway plus one-filing smoke runbook for post-Gateway/Qdrant validation.
- [x] Add validation CLI for SQLite FTS, Qdrant count, citation anchor, and document summary checks.
- [ ] Run single-ticker ingestion for the selected semiconductor demo ticker 10-K one-year test.
- [ ] Run full demo ingestion for the final NIM-era portfolio tickers with 10-K and latest 10-Q filings.
- [ ] Verify SQLite `chunks` count matches `chunks_fts` count.
- [ ] Verify Qdrant point count is close to SQLite chunk count.
- [ ] Create Qdrant snapshot after successful full ingestion.
- [ ] Create `fincontext_demo.db` backup after successful full ingestion.
- [ ] Manually inspect 20 random citation anchors and source URLs for correctness.
- [x] Build `packages/evals/fixtures/labeled_queries.json` with at least 20 query-to-relevant-citation labels.
- [x] Build `packages/evals/fixtures/known_changes.json` with at least 10 known disclosure changes.

## Collaboration Tasks

- [x] With Sunil: confirm SQLite and Qdrant payload schemas before the first full ingestion run.
- [ ] With Sunil: restore snapshot on a clean VM or local environment and verify retrieval determinism.
- [x] With Kishan: provide sample retrieved chunks for UI citation-card rendering.
- [ ] With Kishan: identify at least 2-3 strong semiconductor disclosure changes for the hero demo.
- [ ] With Kishan: tune retrieval queries and section filters for semiconductor supply-chain and customer-concentration questions.
- [ ] With Sunil and Kishan: decide fallback tickers if any demo ticker has poor EDGAR parsing quality.

## Integration Tasks

- [ ] Load final Qdrant snapshot and SQLite DB on the backend host before demo rehearsals.
- [ ] Run retrieval smoke query for semiconductor supply-chain and third-party manufacturing risk.
- [ ] Run retrieval smoke query for export controls and advanced AI accelerator risk.
- [ ] Run retrieval smoke query: `NVDA customer concentration supply chain risk`.
- [ ] Verify all smoke queries return relevant citation-ready chunks.
- [ ] Support Day 8 demo rehearsal by fixing parsing, chunking, or citation issues discovered in the UI.

---

# Tasks for Kishan

## Atomic Tasks

- [x] Create `services/inference-gateway/requirements.txt` with `fastapi`, `uvicorn`, `httpx`, `pydantic`, `structlog`, and `pytest`.
- [x] Implement `services/inference-gateway/main.py` with FastAPI route mounting.
- [x] Implement `router.py` with model routing: `fincontext-reasoner` and `fincontext-planner` to NVIDIA NIM, `fincontext-embedding` to the embedding backend, and `fincontext-reranker` to the reranker backend.
- [x] Implement `middleware.py` for request IDs and latency logging.
- [x] Implement `metrics.py` with in-memory rolling metrics for last 1000 requests.
- [x] Implement `POST /v1/chat/completions` proxy with OpenAI-compatible request/response passthrough.
- [x] Implement `POST /v1/embeddings` proxy for embedding backend.
- [x] Implement `POST /v1/rerank` proxy for reranker backend.
- [x] Implement `GET /health` checking all backend services.
- [x] Implement `GET /metrics` returning average latency, token counts, time-to-first-token, and tokens/sec by model.
- [x] Add Inference Gateway tests with mocked backend services.
- [x] Implement `services/agent-api/app/clients/gateway.py` with async chat, embedding, and rerank helpers.
- [x] Implement `services/agent-api/app/retrieval.py` hybrid retrieval: BM25, Qdrant vector search, RRF merge, rerank, and diversity filter.
- [ ] Add `GET /api/retrieve` debug endpoint for development.
- [x] Write retrieval unit tests for RRF merge and diversity filter.
- [ ] Write retrieval integration test against local Qdrant and SQLite seed data.
- [x] Implement `services/agent-api/app/graph.py` with the 4-node LangGraph sequence.
- [x] Implement `portfolio_context_planner` node with NIM planner structured retrieval-plan output and fallback plan.
- [x] Implement `filing_retrieval` node using the hybrid retrieval module.
- [x] Implement `disclosure_change` node with text normalization, comparison grouping, NIM planner structured classification, and low-confidence filtering.
- [x] Implement `analyst_memo` node with risk score computation, NIM reasoner memo generation, citation verification, planner fallback, and hardcoded disclaimer.
- [ ] Add isolated unit tests for all 4 LangGraph nodes with mocked Gateway and DB/Qdrant clients.
- [x] Add `GET /api/findings/{portfolio_id}` endpoint.
- [x] Add `GET /api/diff/{ticker}` endpoint.
- [x] Add `POST /api/chat` SSE endpoint for citation-backed Q&A.
- [x] Add `GET /api/documents/{ticker}` endpoint for filing explorer.
- [x] Add `GET /api/benchmark/metrics` endpoint combining Gateway metrics and provider status.
- [x] Create `apps/demo-ui/package.json` with React, Vite, Vitest, and frontend dependencies.
- [x] Create `apps/demo-ui/src/lib/apiClient.js` for calls to Agent API.
- [x] Build React Portfolio Upload tab.
- [x] Build React Analysis tab with job creation and status refresh.
- [x] Build React Evidence/Filing Explorer tab listing ingested documents by ticker.
- [x] Build React Disclosure Diff tab with ticker/section/year controls and change cards.
- [x] Build React Risk Scores tab with score table and color coding.
- [x] Build React Analyst Memo tab with memo rendering and disclaimer.
- [ ] Build React Chat tab with SSE streaming.
- [x] Build React Inference Metrics tab with tokens/sec, latency, provider status, and cost proxy placeholders.
- [ ] Replace stale legacy benchmark labels and GPU-memory placeholders with NVIDIA NIM provider/latency metrics in Agent API and React UI.
- [x] Add HuggingFace Space README frontmatter and NVIDIA NIM inference story to `apps/demo-ui/README.md`.
- [ ] Deploy React app to HuggingFace Spaces and configure `AGENT_API_URL` and `AGENT_API_KEY` secrets.

## Collaboration Tasks

- [x] With Sunil: finalize API payloads consumed by React before wiring UI components.
- [ ] With Sunil: confirm authentication and HTTPS behavior between HuggingFace Spaces and Agent API.
- [x] With Abhiyan: verify retrieved chunk payload has all fields needed by memo generation and citation cards.
- [ ] With Abhiyan: choose the best semiconductor disclosure diff examples for the demo script.
- [x] With Sunil and Abhiyan: review citation verification behavior on generated memo outputs.
- [x] With Sunil and Abhiyan: agree on benchmark scenarios and labels shown in the UI.

## Integration Tasks

- [x] Run full graph smoke test: portfolio_context_planner → filing_retrieval → disclosure_change → analyst_memo.
- [x] Verify full analysis returns `risk_scores`, `memo`, `disclosure_changes`, and `citation_pass_rate` in fallback graph tests.
- [x] Verify unsupported memo citations are removed during post-processing logic.
- [ ] Verify every React tab works against the deployed backend host.
- [ ] Verify Chat tab streams tokens and renders citation cards after completion.
- [ ] Verify Benchmark tab shows real measured metrics, not placeholders.
- [ ] Polish UI loading states, error states, and demo copy before final rehearsal.

---

# Cross-Team Collaboration Tasks

- [x] **Architecture lock:** Sunil, Abhiyan, and Kishan confirm no separate edge/API platform or second frontend will be started; React in `apps/demo-ui/` is the demo UI.
- [x] **Schema lock:** `AnalysisState`, API schemas, SQLite schema, and Qdrant payload schema all finalized and merged to `dev` in `packages/schemas/python/`.
- [x] **Data contract review:** Abhiyan and Kishan validate that ingestion outputs are sufficient for retrieval, diff classification, memo generation, and citation cards.
- [x] **Prompt review:** Sunil and Kishan review planner, diff classifier, and memo prompts for structured output, citation discipline, and compliance.
- [x] **Compliance review:** All engineers verify no endpoint or UI text produces buy/sell/hold/short recommendations.
- [ ] **Demo corpus review:** All engineers manually inspect the final NIM-era portfolio ingestion quality and remove problematic documents if needed.
- [ ] **Benchmark review:** All engineers agree on final benchmark numbers and confirm they came from Gateway metrics.
- [ ] **Build-in-public posts:** All engineers provide screenshots, numbers, and technical notes for three posts tagged `#HuggingFace`, `#LangGraph`, and `#NVIDIA`.

---

# Final Integration Tasks

- [ ] Run all service tests: schemas, ingestion worker, inference gateway, agent API, retrieval, and LangGraph node tests.
- [ ] Run all evals: retrieval recall, citation precision, disclosure diff quality, latency benchmark, and risk score stability.
- [ ] Confirm retrieval recall is at least `0.70` and citation precision is at least `0.85`.
- [ ] Confirm the demo portfolio analysis finishes in under 90 seconds or prepare a pre-run fallback.
- [ ] Confirm the disclosure diff tab shows at least 2 real semiconductor disclosure changes with citation anchors.
- [ ] Confirm the analyst memo has citations, evidence table, limitations, confidence, and hardcoded disclaimer.
- [ ] Confirm risk scores include score, delta, confidence, drivers, citations, and portfolio impact.
- [ ] Confirm HuggingFace Space is public and loads from a clean browser session.
- [ ] Confirm backend is reachable from HuggingFace Spaces over HTTPS.
- [ ] Confirm only Agent API is externally reachable; internal model ports remain private.
- [ ] Record 3-5 minute demo video following `docs/demo-plan.md`.
- [ ] Do final rehearsal using the 9-step demo script.
- [ ] Publish three build-in-public posts.
- [ ] Complete lablab.ai final submission with Space URL, GitHub URL, demo video, architecture explanation, NVIDIA NIM inference usage, and HuggingFace integration.

---

# Stretch Tasks

Do not start these until the core MVP is demo-ready.

- [ ] Add 8-K filing ingestion for material event alerts.
- [ ] Add pre-downloaded earnings transcript samples.
- [ ] Add peer comparison by sector.
- [ ] Add historical risk score chart.
- [ ] Add one specific PDF investor-presentation parser for Track 3 extension.
- [ ] Add a second demo portfolio for comparison.
