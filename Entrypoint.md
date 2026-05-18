# FinContext Agent

Portfolio-aware financial intelligence platform for AMD Developer Hackathon 2026, Track 1: AI Agents & Agentic Workflows.

FinContext Agent ingests SEC filings from EDGAR, detects material disclosure changes year-over-year, scores holding-level risk, and produces citation-grounded analyst memos via a 4-agent LangGraph workflow with NVIDIA NIM-backed inference.

## Architecture

```
HuggingFace Spaces (demo UI)
  └── Gradio app → calls Agent API over HTTPS

Backend host (app, retrieval, and storage)
  ├── Agent API (port 8090)      FastAPI + LangGraph, 4-node agent graph
  ├── Inference Gateway (8080)   FastAPI proxy to NVIDIA NIM + local retrieval models
  ├── NIM reasoner               Qwen2.5-72B-Instruct compatible endpoint
  ├── NIM planner                Qwen2.5-7B-Instruct compatible endpoint
  ├── Embeddings                 Local retrieval embeddings
  ├── Reranker                   Local reranking/scoring
  ├── Qdrant (6333)              Vector store, Docker
  └── SQLite (on-disk)           Metadata: portfolios, holdings, jobs, findings
```

The inference boundary is provider-agnostic: Agent API and ingestion code call the Gateway, and the Gateway routes chat completions to NVIDIA NIM hosted endpoints.

## Directory Layout

```text
.
  services/
    agent-api/         FastAPI + LangGraph agent orchestration
    ingestion-worker/  SEC EDGAR fetch, parse, chunk, embed → Qdrant + SQLite
    inference-gateway/ FastAPI proxy to NIM, embedding, reranker services
  apps/
    demo-ui/           Gradio demo app — deployed to HuggingFace Spaces
  packages/
    schemas/           Shared Pydantic models
    evals/             Retrieval recall, citation precision, latency benchmarks
  infra/
    amd-gpu/           Legacy Docker Compose for local model services + Qdrant
    schema.sql         SQLite schema
  configs/
    .env.example
  demo/
    seed_portfolio.csv Demo portfolio: AMD, NVDA, MSFT, JPM, TSLA
  docs/
```

## Quick Start

```bash
# 1. Configure environment
cp configs/.env.example .env   # fill NIM_API_KEY, SEC_USER_AGENT, AGENT_API_KEY

# 2. Start Qdrant
docker compose -f infra/amd-gpu/docker-compose.yml up -d qdrant

# 3. Apply SQLite schema
sqlite3 fincontext.db < infra/schema.sql

# 4. Pre-ingest demo data (run once before demo)
cd services/ingestion-worker
pip install -r requirements.txt
python ingest.py --tickers AMD,NVDA,MSFT,JPM,TSLA --filing-types 10-K,10-Q --years 4

# 5. Start services
cd services/inference-gateway && uvicorn main:app --port 8080 &
cd services/agent-api && uvicorn main:app --port 8090 &

# 6. Verify
curl http://localhost:8090/health
```

## Document Map

| Document | Content |
|----------|---------|
| [Architecture](docs/architecture.md) | System design, request lifecycle, data flow |
| [Agent Design](docs/agent-design.md) | 4-node LangGraph graph, per-node implementation spec |
| [Component Build Plan](docs/component-build-plan.md) | Ordered build steps with tests per step |
| [Milestones](docs/milestones.md) | 9-day hackathon timeline, day-by-day deliverables |
| [Data and Retrieval](docs/data-and-retrieval.md) | EDGAR ingestion, chunking, hybrid retrieval, Qdrant schema |
| [NVIDIA NIM Plan](docs/nvidia-nim-plan.md) | Hosted inference routing, Gateway contract, metrics |
| [Deployment](docs/deployment.md) | Backend setup, HuggingFace Spaces deployment, networking |
| [API Contracts](docs/api-contracts.md) | All FastAPI endpoint specs with request/response examples |
| [Demo Plan](docs/demo-plan.md) | 9-step demo script, screen-by-screen UI description, judge talking points |
| [Risk Scoring](docs/risk-scoring.md) | Risk score formula, categories, output schema |
| [Product Scope](docs/product-scope.md) | MVP definition, non-goals, user stories |
| [Security](docs/security-compliance.md) | Auth, compliance rules, investment disclaimer requirements |
| [References](docs/references.md) | Research papers, tools, and resources cited |

## Why This Architecture Is Focused

The current plan keeps app services, storage, retrieval, and orchestration simple while routing LLM inference through NVIDIA NIM. That keeps the hackathon build small enough to finish and lets the demo focus on the disclosure-drift workflow plus the HuggingFace Spaces UI.

## HuggingFace Integration

- Models: NIM-hosted Qwen-compatible chat models for planning and memo generation, plus local retrieval embeddings/reranking
- Demo UI deployed as a public HuggingFace Space
- `NIM_API_KEY` used for hosted inference access
