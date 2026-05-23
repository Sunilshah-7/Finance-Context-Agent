# FinContext Agent

Portfolio-aware financial intelligence platform for AMD Developer Hackathon 2026, Track 1: AI Agents & Agentic Workflows.

FinContext Agent ingests SEC filings from EDGAR, detects material disclosure changes year-over-year, scores holding-level risk, and produces citation-grounded analyst memos via a 4-agent LangGraph workflow running on AMD Developer Cloud.

## Architecture

```
HuggingFace Spaces (demo UI)
  └── React Static Space → calls Agent API over HTTPS

AMD Developer Cloud VM (all compute and storage)
  ├── Agent API (port 8090)      FastAPI + LangGraph, 4-node agent graph
  ├── Inference Gateway (8080)   FastAPI proxy — routes to local vLLM or NVIDIA NIM
  ├── vLLM reasoner (8000)       Qwen2.5-72B-Instruct, FP16, ROCm  [local path]
  ├── vLLM planner (8001)        Qwen2.5-14B-Instruct, FP16, ROCm  [local path]
  ├── Embeddings (8002)          BAAI/bge-large-en-v1.5, TEI
  ├── Reranker (8003)            BAAI/bge-reranker-large, TEI
  ├── Qdrant (6333)              Vector store, Docker
  └── SQLite (on-disk)           Metadata: portfolios, holdings, jobs, findings
```

AMD MI300X has 192 GB of HBM3 VRAM. Qwen2.5-72B runs in FP16 on a single GPU without tensor parallelism, with a full 65,536-token context window. An entire 10-K annual report processes in a single context pass.

## Directory Layout

```text
.
  services/
    agent-api/         FastAPI + LangGraph agent orchestration
    ingestion-worker/  SEC EDGAR fetch, parse, chunk, embed → Qdrant + SQLite
    inference-gateway/ FastAPI proxy to vLLM, embedding, reranker services
  apps/
    demo-ui/           Vite React app — deployed as HuggingFace Static Space
  packages/
    schemas/           Shared Pydantic models
    evals/             Retrieval recall, citation precision, latency benchmarks
  infra/
    amd-gpu/           Docker Compose: all model services + Qdrant
    schema.sql         SQLite schema
  configs/
    .env.example
  demo/
    seed_portfolio.csv Demo portfolio: AMD, NVDA, MSFT, JPM, TSLA
  docs/
```

## Quick Start (AMD VM)

```bash
# 1. Start all model services
cd infra/amd-gpu
cp ../../configs/.env.example .env   # fill HF_TOKEN
docker compose up -d
# Wait 3-5 minutes for 72B model to load

# 2. Apply SQLite schema
sqlite3 ../fincontext.db < ../infra/schema.sql

# 3. Pre-ingest demo data (run once before demo)
cd services/ingestion-worker
pip install -r requirements.txt
python ingest.py --tickers AMD,NVDA,MSFT,JPM,TSLA --filing-types 10-K,10-Q --years 4

# 4. Start services
cd services/inference-gateway && uvicorn main:app --port 8080 &
cd services/agent-api && uvicorn main:app --port 8090 &

# 5. Verify
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
| [AMD GPU Plan](docs/amd-gpu-plan.md) | Hardware story, vLLM setup, ROCm troubleshooting, cost management |
| [Deployment](docs/deployment.md) | AMD VM setup, HuggingFace Spaces deployment, networking |
| [API Contracts](docs/api-contracts.md) | All FastAPI endpoint specs with request/response examples |
| [Demo Plan](docs/demo-plan.md) | 9-step demo script, screen-by-screen UI description, judge talking points |
| [Risk Scoring](docs/risk-scoring.md) | Risk score formula, categories, output schema |
| [Product Scope](docs/product-scope.md) | MVP definition, non-goals, user stories |
| [Security](docs/security-compliance.md) | Auth, compliance rules, investment disclaimer requirements |
| [References](docs/references.md) | Research papers, tools, and resources cited |

## Why This Architecture Is Focused

The current plan keeps compute, storage, retrieval, and orchestration on one AMD Developer Cloud VM. That keeps the hackathon build small enough to finish, avoids cross-cloud service wiring, and lets the demo focus on AMD GPU inference plus the HuggingFace Spaces UI.

## HuggingFace Integration

- Models: `Qwen/Qwen2.5-72B-Instruct`, `Qwen/Qwen2.5-14B-Instruct`, `BAAI/bge-large-en-v1.5`, `BAAI/bge-reranker-large` — all from HuggingFace Hub
- Demo UI deployed as a public HuggingFace Space
- `HF_TOKEN` used for authenticated model downloads
