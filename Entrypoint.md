# FinContext Agent

Portfolio-aware financial intelligence platform for AMD Developer Hackathon
2026, Track 1: AI Agents & Agentic Workflows.

FinContext Agent ingests SEC filings from EDGAR, detects disclosure changes,
scores holding-level research risk, and produces citation-grounded analyst
memos through a 4-node LangGraph workflow.

## Architecture

```text
HuggingFace Spaces
  React Static Space
    |
    v
Backend host
  Agent API (8090)        FastAPI + LangGraph
  Inference Gateway (8080) Proxy to NVIDIA NIM + retrieval backends
  Qdrant (6333)           Vector store
  SQLite                  Portfolios, filings, chunks, jobs, findings

NVIDIA NIM
  fincontext-planner      Qwen2.5-14B compatible endpoint
  fincontext-reasoner     Qwen2.5-72B compatible endpoint
```

The Gateway is the inference boundary. Agent API and ingestion code call the
Gateway; they do not call NVIDIA NIM or retrieval model services directly.

## Quick Start

```bash
cp configs/.env.example .env   # fill NIM_API_KEY, SEC_USER_AGENT, AGENT_API_KEY
docker compose -f infra/docker-compose.yml up -d qdrant
sqlite3 fincontext.db < infra/schema.sql
python3 infra/qdrant/init_collection.py
```

Start services:

```bash
cd services/inference-gateway && uvicorn main:app --port 8080 &
cd services/agent-api && uvicorn main:app --port 8090 &
curl http://localhost:8090/health
```

## Document Map

| Document | Content |
|----------|---------|
| [Architecture](docs/architecture.md) | System design, request lifecycle, data flow |
| [Agent Design](docs/agent-design.md) | 4-node LangGraph graph |
| [NVIDIA NIM Plan](docs/nvidia-nim-plan.md) | Hosted inference routing and Gateway contract |
| [Deployment](docs/deployment.md) | Backend, Space, and NIM setup |
| [API Contracts](docs/api-contracts.md) | FastAPI endpoint specs |
| [Demo Plan](docs/demo-plan.md) | Judge-facing demo flow |
