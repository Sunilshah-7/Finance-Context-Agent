# FinContext Agent

FinContext Agent is an AMD Developer Hackathon 2026 project for Track 1:
AI Agents and Agentic Workflows.

The project turns SEC filings into citation-grounded portfolio analysis. It
pre-ingests 10-K and 10-Q filings from EDGAR, detects changes in disclosure
language over time, scores holding-level risk, and produces analyst-style memos
that cite exact filing chunks.

This repository is no longer a collection of project ideas. It is the working
repo for the FinContext Agent MVP.

## What The Product Does

A user uploads a portfolio such as:

```text
AMD, NVDA, MSFT, JPM, TSLA
```

The system then answers questions like:

```text
What changed in supply-chain or customer concentration risk for my semiconductor holdings?
```

The answer should not be generic. It should point to evidence from SEC filings,
for example:

```text
AMD 10-K Item 1A paragraph 42
```

The required disclaimer is:

```text
This output is research assistance only and does not constitute investment advice.
```

The system never gives buy, sell, hold, or short recommendations.

## Inference Architecture

The original architecture was designed around local GPU inference. The live MVP now uses a provider-agnostic inference layer backed by NVIDIA NIM hosted inference endpoints.

The important architectural story is the abstraction boundary: Agent API and ingestion code call the Inference Gateway, and the Gateway routes model requests to NVIDIA NIM-compatible OpenAI endpoints. This lets the app keep the same LangGraph, retrieval, citation, Qdrant, and SQLite design while changing the inference provider.

The original planned model split was:

- Qwen2.5-14B for planning and disclosure-change classification.
- Qwen2.5-72B for the final analyst memo generation.
- BAAI/bge-large-en-v1.5 for embeddings.
- BAAI/bge-reranker-large for reranking retrieval candidates.

The original model IDs came from Hugging Face. The current live stack uses NIM-hosted chat models plus local embeddings for retrieval.

## System Architecture

Due to hosted-inference availability during the hackathon period, the live MVP uses a provider-agnostic inference architecture built around NVIDIA NIM endpoints.

The architecture itself remains unchanged.

Only the inference backend provider was swapped.

This preserves:

- LangGraph orchestration
- Retrieval architecture
- Citation grounding
- Qdrant vector search
- SQLite BM25 retrieval
- FastAPI services
- Inference Gateway abstraction

The project is still compatible with future local GPU deployment because the Inference Gateway preserves a provider-neutral contract.

## Current Model Stack

The current hosted inference split is:

- Qwen2.5-7B-Instruct for planning and intermediate reasoning
- Qwen2.5-72B-Instruct for final analyst memo generation
- Local embedding model for retrieval embeddings
- Reciprocal Rank Fusion plus reranking retrieval pipeline

The system uses:

- NVIDIA NIM hosted inference APIs for LLM inference
- Local CPU embeddings for lightweight retrieval generation
- Qdrant for semantic vector search
- SQLite FTS5 for BM25 keyword retrieval

## System Architecture

The demo UI runs on HuggingFace Spaces. The app services run on the backend host, while LLM inference is served by NVIDIA NIM hosted endpoints:

```text
HuggingFace Space
  Gradio UI
    |
    v
Agent API, port 8090
  FastAPI plus LangGraph workflow
    |
    v
Inference Gateway, port 8080
  Provider abstraction layer
    |
    +-- NVIDIA NIM hosted inference
    |     Qwen2.5-72B-Instruct
    |     Qwen2.5-7B-Instruct
    |
    +-- Local embedding service
    |
    +-- Qdrant vector store, port 6333
    |
    +-- SQLite file, fincontext.db
```

Important rule: Agent API code and ingestion code call the Inference Gateway.
They do not call NVIDIA NIM, local embedding code, or retrieval services directly.

## Current Build State

Merged into `dev`:

- Shared schema package under `packages/schemas`.
- SQLite schema under `infra/schema.sql`.
- Qdrant collection init script.
- Ingestion worker foundation.
- Inference Gateway foundation.
- Demo-data backup and snapshot ops.
- Ingestion validation helpers.
- Human-readable handoff and ingestion output contract docs.

Open or pending:

- Agent API PR #19 is marked "DONOT MERGE THIS PR: Still in review".
- Validation CLI PR #24 is open for review.
- Eval fixture scaffolding PR #23 is open for review.
- Real NIM-backed ingestion has not run yet.
- Demo corpus has not been loaded into Qdrant/SQLite yet.

## Repository Map

```text
services/
  ingestion-worker/      EDGAR fetch, SEC HTML parse, chunk, embed, write data
  inference-gateway/     FastAPI proxy to NIM chat models, embeddings, and reranker
  agent-api/             FastAPI plus LangGraph analysis workflow

apps/
  demo-ui/               Gradio UI for HuggingFace Spaces

packages/
  schemas/               Shared Pydantic state, DB, and API contracts
  evals/                 Retrieval/diff/citation benchmark docs and fixtures

infra/
  schema.sql             SQLite tables, indexes, and FTS5 triggers
  qdrant/                Qdrant collection initialization
  ops/                   Demo backup and snapshot helpers

docs/
  architecture.md
  agent-design.md
  data-and-retrieval.md
  ingestion-output-contract.md
  fincontext-agent-explained.md
```

## Start Here If You Are New

Read these in order:

1. `docs/fincontext-agent-explained.md`
2. `docs/codex-work-handoff.md`
3. `docs/ingestion-output-contract.md`
4. `docs/architecture.md`
5. `TODO.md`

The first document explains the project from the ground up. The handoff doc
explains what was built by agents and why. The ingestion output contract tells
Kishan and retrieval/UI work exactly what data exists after ingestion.

## Ingestion In Plain English

Ingestion means: before the live demo, we download SEC filings and turn them
into searchable evidence.

The ingestion worker does this:

1. Resolve a ticker like `AMD` to its SEC CIK.
2. Fetch the company's filing list from EDGAR.
3. Download recent 10-K and 10-Q HTML filings.
4. Parse sections like Item 1A Risk Factors.
5. Split long sections into smaller chunks.
6. Give every chunk a citation anchor.
7. Send chunk text to the Inference Gateway for embeddings.
8. Store chunk text in SQLite for keyword search.
9. Store vectors in Qdrant for semantic search.

That is why retrieval later works efficiently. The data is already shaped for retrieval.

## Retrieval In Plain English

Retrieval means: given a question, find the most relevant SEC filing chunks.

The intended retrieval flow is:

1. Turn the user's question into an embedding.
2. Search Qdrant for semantically similar chunks.
3. Search SQLite FTS5 for keyword/BM25 matches.
4. Merge those candidate lists with Reciprocal Rank Fusion.
5. Send candidate chunk texts to the Gateway reranker.
6. Return the best chunks with text, source URL, and citation anchor.

## Local Checks

Run focused checks for the parts that already exist. Install each service's
requirements first if the local environment does not already have them.

```bash
python3 -m pytest services/ingestion-worker/tests -x
python3 -m pytest services/inference-gateway/tests -x
python3 -m pytest infra/tests -x
```

Some future tests will require Qdrant, Gateway, or live model
services. The current foundation tests mostly use mocked HTTP and temporary
SQLite files.

After PR #23 merges, eval fixture checks can also run with:

```bash
python3 -m pytest packages/evals/tests -x
```

## Branch And PR Rules

- Branch from `dev`.
- Open PRs back into `dev`.
- Do not commit directly to `dev` or `main`.
- Do not self-merge without teammate review.
- Do not commit `.env`, `fincontext.db`, Qdrant storage, model cache, or secrets.
- Commit messages should be atomic, for example:

```text
feat(ingestion): add validation CLI
docs(project): add beginner explainer
eval(evals): add retrieval fixture scaffolding
```

## Useful Docs

| Document                             | Purpose                                       |
| ------------------------------------ | --------------------------------------------- |
| `docs/fincontext-agent-explained.md` | Beginner-friendly full project explanation    |
| `docs/codex-work-handoff.md`         | What agent-built branches added and why       |
| `docs/ingestion-output-contract.md`  | SQLite/Qdrant fields used by retrieval and UI |
| `docs/data-and-retrieval.md`         | Retrieval architecture and Qdrant/BM25 design |
| `docs/agent-design.md`               | LangGraph node specs                          |
| `docs/api-contracts.md`              | Agent API request and response contracts      |
| `docs/nvidia-nim-plan.md`            | NIM routing, Gateway contract, and metrics    |
| `docs/demo-data-ops.md`              | SQLite backup and Qdrant snapshot commands    |
| `docs/demo-plan.md`                  | Judge-facing demo flow                        |
