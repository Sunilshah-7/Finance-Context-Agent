# TODO

Task plan for completing FinContext Agent with three engineers: Sunil, Abhiyan, and Kishan.

This plan follows `AGENTS.md` as the source of truth. Build the current architecture: one AMD Developer Cloud VM running FastAPI, LangGraph, vLLM/ROCm, TEI, Qdrant, and SQLite, with a public Gradio demo on HuggingFace Spaces.

Do not build a separate edge/API platform or JavaScript frontend. The project uses the Agent API on the AMD VM and a Gradio app in `apps/demo-ui/`.

## Task Types

- **Atomic task:** Independent task one engineer can complete without blocking another engineer.
- **Collaboration task:** Requires two or more engineers to agree on schema, API behavior, prompts, data shape, or demo expectations.
- **Integration task:** Final assembly or verification across multiple components.

## Task Ownership Summary

| Engineer | Primary Ownership |
| --- | --- |
| Sunil | AMD VM, infrastructure, schema, Agent API skeleton, deployment, final submission |
| Abhiyan | EDGAR ingestion, parsing, chunking, embeddings, Qdrant/SQLite indexing, retrieval quality |
| Kishan | Inference Gateway, LangGraph nodes, Gradio UI, benchmark panel, demo polish |

## Shared Rules

- [x] Work on feature branches; never commit directly to `main` or `dev`. All PRs target `dev`.
- [ ] Do not commit `.env`, `fincontext.db`, Qdrant storage, model cache, or secrets.
- [ ] Use Python 3.12 and Pydantic models from `packages/schemas/python/`.
- [ ] Every service-to-service model call must go through the Inference Gateway on port `8080`.
- [ ] Use Qwen2.5-14B for planner/diff calls and Qwen2.5-72B only for final memo generation.
- [ ] Every factual memo claim must have a valid citation mapped to a retrieved chunk.
- [ ] Never generate buy/sell/hold/short recommendations.
- [ ] Pre-ingest demo data before the live demo; do not demo live EDGAR ingestion.

---

# Tasks for Sunil

## Atomic Tasks

- [x] Create or verify `.gitignore` includes `.env`, `fincontext.db`, `fincontext_demo.db`, `/models/`, `qdrant_storage/`, `__pycache__/`, `.venv/`, and `*.pyc`.
- [x] Create `configs/.env.example` for the current architecture with `AMD_VM_PUBLIC_IP`, `AGENT_API_KEY`, `VLLM_REASONER_URL`, `VLLM_PLANNER_URL`, `EMBEDDING_URL`, `RERANKER_URL`, `INFERENCE_GATEWAY_URL`, `QDRANT_URL`, `QDRANT_COLLECTION`, `SQLITE_DB_PATH`, `HF_TOKEN`, `HF_HOME`, `SEC_USER_AGENT`, `ENVIRONMENT`, and `LOG_LEVEL`.
- [x] Create `infra/schema.sql` for SQLite tables: `portfolios`, `holdings`, `documents`, `chunks`, `chunks_fts`, `analysis_jobs`, and `findings`.
- [x] Add FTS5 triggers in `infra/schema.sql` so inserts into `chunks` populate `chunks_fts`.
- [x] Create `infra/amd-gpu/docker-compose.yml` with services for `vllm-72b`, `vllm-14b`, `tei-embedding`, `tei-reranker`, and `qdrant`.
- [x] Add Qdrant collection initialization script for `fincontext_chunks` with 1024 dimensions and payload indexes for `ticker`, `filing_type`, `filed_at`, and `section`.
- [ ] Provision AMD Developer Cloud VM with AMD Instinct GPU, Ubuntu, ROCm, Docker, and enough disk for models and Qdrant data.
- [ ] Verify AMD GPU visibility with `rocm-smi`.
- [ ] Start GPU/storage services with Docker Compose and verify health for ports `8000`, `8001`, `8002`, `8003`, and `6333`.
- [x] Create `packages/schemas/python/state.py` with `AnalysisState`, `Holding`, `RetrievalPlan`, `EvidenceChunk`, `DisclosureChange`, `RiskScore`, `Citation`, and `AnalystMemo`.
- [x] Create `packages/schemas/python/db.py` for SQLite row models.
- [x] Create `packages/schemas/python/api.py` for FastAPI request/response models from `docs/api-contracts.md`.
- [x] Add `packages/schemas` packaging files so services can install it with `pip install -e ../../packages/schemas`.
- [ ] Create `services/agent-api/main.py` with FastAPI app and `GET /health`.
- [ ] Implement Agent API bearer-token authentication using `AGENT_API_KEY`.
- [ ] Implement `POST /api/portfolio/upload` to parse CSV, validate required columns, resolve basic portfolio totals, and write portfolio/holdings rows.
- [ ] Implement `POST /api/analyze` job creation with initial async background-task stub.
- [ ] Implement `GET /api/jobs/{job_id}` to read job status from SQLite.
- [ ] Implement Agent API SQLite client functions for portfolios, holdings, documents, chunks, jobs, findings, and benchmark reads.
- [ ] Add basic Agent API tests for health, portfolio upload validation, job creation, and job status.
- [ ] Configure firewall/reverse proxy so only Agent API port `8090` is externally reachable.
- [ ] Set up HTTPS for Agent API with nginx or a tested tunnel fallback.
- [ ] Create Qdrant snapshot and SQLite backup commands in an ops note or script.
- [ ] Update root README with final architecture, setup commands, demo URL placeholder, and submission instructions.

## Collaboration Tasks

- [ ] With Abhiyan: finalize SQLite `documents` and `chunks` columns before ingestion writes data.
- [ ] With Abhiyan: verify `citation_anchor` format exactly matches `{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}` or table equivalent.
- [ ] With Kishan: finalize Agent API response schemas for Gradio tabs before UI wiring.
- [ ] With Kishan: agree on job stages and progress values: `planning`, `retrieving`, `analyzing`, `writing`, `complete`.
- [ ] With Abhiyan and Kishan: review `AnalysisState` before any agent node implementation starts.
- [ ] With Abhiyan and Kishan: define demo seed portfolio and confirm all tickers are pre-ingested.

## Integration Tasks

- [ ] Apply `infra/schema.sql` to create `fincontext.db` on the AMD VM.
- [ ] Start full AMD VM stack and publish service health checklist.
- [ ] Restore or verify Qdrant and SQLite demo snapshots on the AMD VM.
- [ ] Run end-to-end smoke test: upload portfolio → create job → graph starts → job completes.
- [ ] Verify HuggingFace Space can reach Agent API over HTTPS with bearer auth.
- [ ] Run final security check: no secrets committed, only required port exposed, disclaimer always present.
- [ ] Prepare final lablab.ai submission: project description, architecture, AMD GPU story, HuggingFace integration, GitHub repo, demo video, and Space URL.

---

# Tasks for Abhiyan

## Atomic Tasks

- [x] Create `services/ingestion-worker/requirements.txt` with `httpx`, `beautifulsoup4`, `lxml`, `tiktoken`, `qdrant-client`, `pydantic`, and `pytest`.
- [x] Implement `worker/models.py` for `FilingRef`, `NormalizedDocument`, `NormalizedSection`, `ChunkInput`, and `ChunkWithEmbedding`.
- [x] Implement `worker/sec_client.py` with async EDGAR client, required `SEC_USER_AGENT`, ticker-to-CIK cache, submissions fetch, filing filtering, and document download.
- [x] Add SEC rate limiter capped at 10 requests per second with polite delay for document downloads.
- [x] Add local EDGAR HTML cache to avoid repeated downloads during development.
- [x] Write `test_sec_client.py` verifying AMD resolves to CIK `0000002488`.
- [x] Implement `worker/parsers/sec_html.py` using BeautifulSoup/lxml to extract `Item 1`, `Item 1A`, `Item 7`, `Item 7A`, and `Item 8`.
- [x] Normalize EDGAR HTML by removing XBRL tags, table-of-contents noise, headers, and repeated whitespace.
- [ ] Add parser fixture for a saved AMD 10-K HTML file.
- [ ] Write parser test verifying AMD `Item 1A` extracts at least 1000 words.
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
- [ ] Implement `ingest.py` CLI with arguments for tickers, filing types, years, DB path, Qdrant URL, and Gateway URL.
- [ ] Run single-ticker ingestion for AMD 10-K one-year test.
- [ ] Run full demo ingestion for AMD, NVDA, MSFT, JPM, and TSLA with 10-K and latest 10-Q filings.
- [ ] Verify SQLite `chunks` count matches `chunks_fts` count.
- [ ] Verify Qdrant point count is close to SQLite chunk count.
- [ ] Create Qdrant snapshot after successful full ingestion.
- [ ] Create `fincontext_demo.db` backup after successful full ingestion.
- [ ] Manually inspect 20 random citation anchors and source URLs for correctness.
- [ ] Build `packages/evals/fixtures/labeled_queries.json` with at least 20 query-to-relevant-citation labels.
- [ ] Build `packages/evals/fixtures/known_changes.json` with at least 10 known disclosure changes.

## Collaboration Tasks

- [ ] With Sunil: confirm SQLite and Qdrant payload schemas before the first full ingestion run.
- [ ] With Sunil: restore snapshot on a clean VM or local environment and verify retrieval determinism.
- [ ] With Kishan: provide sample retrieved chunks for UI citation-card rendering.
- [ ] With Kishan: identify at least 2-3 strong AMD disclosure changes for the hero demo.
- [ ] With Kishan: tune retrieval queries and section filters for semiconductor supply-chain and customer-concentration questions.
- [ ] With Sunil and Kishan: decide fallback tickers if any demo ticker has poor EDGAR parsing quality.

## Integration Tasks

- [ ] Load final Qdrant snapshot and SQLite DB on AMD VM before demo rehearsals.
- [ ] Run retrieval smoke query: `AMD supply chain third party manufacturing risk`.
- [ ] Run retrieval smoke query: `AMD export controls advanced AI accelerators`.
- [ ] Run retrieval smoke query: `NVDA customer concentration supply chain risk`.
- [ ] Verify all smoke queries return relevant citation-ready chunks.
- [ ] Support Day 8 demo rehearsal by fixing parsing, chunking, or citation issues discovered in the UI.

---

# Tasks for Kishan

## Atomic Tasks

- [ ] Create `services/inference-gateway/requirements.txt` with `fastapi`, `uvicorn`, `httpx`, `pydantic`, `structlog`, and `pytest`.
- [ ] Implement `services/inference-gateway/main.py` with FastAPI route mounting.
- [ ] Implement `router.py` with model routing: `fincontext-reasoner` to port `8000`, `fincontext-planner` to port `8001`, `fincontext-embedding` to port `8002`, and `fincontext-reranker` to port `8003`.
- [ ] Implement `middleware.py` for request IDs and latency logging.
- [ ] Implement `metrics.py` with in-memory rolling metrics for last 1000 requests.
- [ ] Implement `POST /v1/chat/completions` proxy with OpenAI-compatible request/response passthrough.
- [ ] Implement `POST /v1/embeddings` proxy for TEI embedding service.
- [ ] Implement `POST /v1/rerank` proxy for TEI reranker service.
- [ ] Implement `GET /health` checking all backend services.
- [ ] Implement `GET /metrics` returning average latency, token counts, time-to-first-token, and tokens/sec by model.
- [ ] Add Inference Gateway tests with mocked backend services.
- [ ] Implement `services/agent-api/app/clients/gateway.py` with async chat, embedding, and rerank helpers.
- [ ] Implement `services/agent-api/app/retrieval.py` hybrid retrieval: BM25, Qdrant vector search, RRF merge, rerank, and diversity filter.
- [ ] Add `GET /api/retrieve` debug endpoint for development.
- [ ] Write retrieval unit tests for RRF merge and diversity filter.
- [ ] Write retrieval integration test against local Qdrant and SQLite seed data.
- [ ] Implement `services/agent-api/app/graph.py` with the 4-node LangGraph sequence.
- [ ] Implement `portfolio_context_planner` node with Qwen2.5-14B structured retrieval-plan output and fallback plan.
- [ ] Implement `filing_retrieval` node using the hybrid retrieval module.
- [ ] Implement `disclosure_change` node with text normalization, comparison grouping, Qwen2.5-14B structured classification, and low-confidence filtering.
- [ ] Implement `analyst_memo` node with risk score computation, Qwen2.5-72B memo generation, citation verification, 14B fallback, and hardcoded disclaimer.
- [ ] Add isolated unit tests for all 4 LangGraph nodes with mocked Gateway and DB/Qdrant clients.
- [ ] Add `GET /api/findings/{portfolio_id}` endpoint.
- [ ] Add `GET /api/diff/{ticker}` endpoint.
- [ ] Add `POST /api/chat` SSE endpoint for citation-backed Q&A.
- [ ] Add `GET /api/documents/{ticker}` endpoint for filing explorer.
- [ ] Add `GET /api/benchmark/metrics` endpoint combining Gateway metrics and GPU info.
- [ ] Create `apps/demo-ui/requirements.txt` with `gradio`, `httpx`, and required plotting/data packages.
- [ ] Create `apps/demo-ui/api_client.py` for authenticated calls to Agent API.
- [ ] Build Gradio Portfolio Upload tab.
- [ ] Build Gradio Analysis tab with job polling every 2 seconds.
- [ ] Build Gradio Filing Explorer tab listing ingested documents by ticker.
- [ ] Build Gradio Disclosure Diff tab with ticker/section/year controls and change cards.
- [ ] Build Gradio Risk Scores tab with score table and color coding.
- [ ] Build Gradio Analyst Memo tab with markdown rendering and citation cards.
- [ ] Build Gradio Chat tab with SSE streaming.
- [ ] Build Gradio AMD Benchmark tab with tokens/sec, latency, GPU memory, and cost proxy.
- [ ] Add HuggingFace Space README frontmatter and AMD hardware story to `apps/demo-ui/README.md`.
- [ ] Deploy Gradio app to HuggingFace Spaces and configure `AGENT_API_URL` and `AGENT_API_KEY` secrets.

## Collaboration Tasks

- [ ] With Sunil: finalize API payloads consumed by Gradio before wiring UI components.
- [ ] With Sunil: confirm authentication and HTTPS behavior between HuggingFace Spaces and Agent API.
- [ ] With Abhiyan: verify retrieved chunk payload has all fields needed by memo generation and citation cards.
- [ ] With Abhiyan: choose the best AMD disclosure diff examples for the demo script.
- [ ] With Sunil and Abhiyan: review citation verification behavior on generated memo outputs.
- [ ] With Sunil and Abhiyan: agree on benchmark scenarios and labels shown in the UI.

## Integration Tasks

- [ ] Run full graph smoke test: portfolio_context_planner → filing_retrieval → disclosure_change → analyst_memo.
- [ ] Verify full analysis returns `risk_scores`, `memo`, `disclosure_changes`, and `citation_pass_rate`.
- [ ] Verify unsupported memo citations are removed during post-processing.
- [ ] Verify every Gradio tab works against the deployed AMD VM.
- [ ] Verify Chat tab streams tokens and renders citation cards after completion.
- [ ] Verify Benchmark tab shows real measured metrics, not placeholders.
- [ ] Polish UI loading states, error states, and demo copy before final rehearsal.

---

# Cross-Team Collaboration Tasks

- [x] **Architecture lock:** Sunil, Abhiyan, and Kishan confirm no separate edge/API platform or JavaScript frontend work will be started.
- [x] **Schema lock:** `AnalysisState`, API schemas, SQLite schema, and Qdrant payload schema all finalized and merged to `dev` in `packages/schemas/python/`.
- [ ] **Data contract review:** Abhiyan and Kishan validate that ingestion outputs are sufficient for retrieval, diff classification, memo generation, and citation cards.
- [ ] **Prompt review:** Sunil and Kishan review planner, diff classifier, and memo prompts for structured output, citation discipline, and compliance.
- [ ] **Compliance review:** All engineers verify no endpoint or UI text produces buy/sell/hold/short recommendations.
- [ ] **Demo corpus review:** All engineers manually inspect AMD/NVDA/MSFT/JPM/TSLA ingestion quality and remove problematic documents if needed.
- [ ] **Benchmark review:** All engineers agree on final benchmark numbers and confirm they were measured on AMD Developer Cloud.
- [ ] **Build-in-public posts:** All engineers provide screenshots, numbers, and technical notes for three posts tagged `#AMDDevHackathon`, `#HuggingFace`, `#LangGraph`, and `#vLLM`.

---

# Final Integration Tasks

- [ ] Run all service tests: schemas, ingestion worker, inference gateway, agent API, retrieval, and LangGraph node tests.
- [ ] Run all evals: retrieval recall, citation precision, disclosure diff quality, latency benchmark, and risk score stability.
- [ ] Confirm retrieval recall is at least `0.70` and citation precision is at least `0.85`.
- [ ] Confirm the demo portfolio analysis finishes in under 90 seconds or prepare a pre-run fallback.
- [ ] Confirm the disclosure diff tab shows at least 2 real AMD changes with citation anchors.
- [ ] Confirm the analyst memo has citations, evidence table, limitations, confidence, and hardcoded disclaimer.
- [ ] Confirm risk scores include score, delta, confidence, drivers, citations, and portfolio impact.
- [ ] Confirm HuggingFace Space is public and loads from a clean browser session.
- [ ] Confirm AMD VM backend is reachable from HuggingFace Spaces over HTTPS.
- [ ] Confirm only Agent API is externally reachable; internal model ports remain private.
- [ ] Record 3-5 minute demo video following `docs/demo-plan.md`.
- [ ] Do final rehearsal using the 9-step demo script.
- [ ] Publish three build-in-public posts.
- [ ] Complete lablab.ai final submission with Space URL, GitHub URL, demo video, architecture explanation, AMD GPU usage, and HuggingFace model usage.

---

# Stretch Tasks

Do not start these until the core MVP is demo-ready.

- [ ] Add 8-K filing ingestion for material event alerts.
- [ ] Add pre-downloaded earnings transcript samples.
- [ ] Add peer comparison by sector.
- [ ] Add historical risk score chart.
- [ ] Add one specific PDF investor-presentation parser for Track 3 extension.
- [ ] Add a second demo portfolio for comparison.
