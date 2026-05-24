# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project

FinContext Agent is an AMD Developer Hackathon 2026 Track 1 project. It ingests
SEC filings, detects disclosure-language drift, scores holding-level research
risk, and produces citation-grounded analyst memos.

## Current Architecture Decision

This is a prototype. Do not build or assume local 70B GPU inference. The final
plan is NVIDIA NIM for hosted OpenAI-compatible chat completions through the
Inference Gateway.

The backend host runs:

```text
Agent API           port 8090  FastAPI + LangGraph
Inference Gateway   port 8080  Proxy to NVIDIA NIM + retrieval backends
Qdrant              port 6333  Vector store
SQLite              on disk    Metadata and chunk text
```

The public demo UI is the Vite React app in `apps/demo-ui/`, deployed as a
HuggingFace Static Space. The browser calls only the Agent API.

## Commands

```bash
cp configs/.env.example .env
# Fill NIM_API_KEY, NIM_BASE_URL, SEC_USER_AGENT, and AGENT_API_KEY.

docker compose -f infra/docker-compose.yml up -d qdrant
sqlite3 fincontext.db < infra/schema.sql
python3 infra/qdrant/init_collection.py
```

Run services:

```bash
cd services/inference-gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

cd services/agent-api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090
```

Run React demo locally:

```bash
cd apps/demo-ui
npm install
VITE_AGENT_API_URL=http://localhost:8090 npm run dev
```

## Model Allocation

| Task | Gateway model | Backend |
|------|---------------|---------|
| Retrieval planning | `fincontext-planner` | NVIDIA NIM planner model |
| Disclosure classification | `fincontext-planner` | NVIDIA NIM planner model |
| Final analyst memo | `fincontext-reasoner` | NVIDIA NIM reasoner model |
| Embeddings | `fincontext-embedding` | configured embedding backend |
| Reranking | `fincontext-reranker` | configured reranker backend |

All model calls go through the Inference Gateway. Do not call NVIDIA NIM,
embedding backends, rerankers, or Qdrant directly from LangGraph nodes.

## Compliance Rules

- Every factual claim in a memo must have a citation referencing a retrieved chunk.
- Never generate buy, sell, hold, short, or other investment recommendations.
- Every memo must include the research-assistance disclaimer.
- Risk scores must include confidence and citations.
