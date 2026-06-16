# FinContext Agent

Portfolio-aware financial research application for the AMD Developer Hackathon
2026. The current implementation is Go-first and production-shaped, with
curated fixtures keeping the demo deterministic while live ingestion and
retrieval are completed.

`README.md` is the source of truth for the runnable architecture.

## Current Architecture

```text
Browser / HuggingFace Space
  |
  v
Agent API (Go, :8090)
  - serves exported Next.js UI
  - orchestrates fixture-backed agent runs
  - validates citations
  - persists runs and seeded fixture metadata in SQLite
  - checks/initializes Qdrant collection
  - checks Inference Gateway health

Inference Gateway (Go, :8080)
  - POST /v1/chat/completions -> NVIDIA NIM
  - POST /v1/embeddings -> configured embedding backend
  - POST /v1/rerank -> configured reranker backend
  - GET /health
  - GET /metrics

Qdrant (:6333)
  - fincontext_chunks collection, 1024-dimensional cosine vectors

SQLite
  - agent_runs, portfolios, evidence_citations
```

## Quick Start

```bash
cp configs/.env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up --build
```

Open:

```text
http://localhost:8090
```

Health checks:

```bash
curl http://localhost:8090/api/health
curl http://localhost:8080/health
curl http://localhost:6333/healthz
```

## Document Map

| Document | Content |
|----------|---------|
| [README](README.md) | Source of truth: current architecture, services, commands, readiness |
| [Architecture](docs/architecture.md) | Go-first runtime structure and request lifecycle |
| [API Contracts](docs/api-contracts.md) | Current Agent API and Gateway endpoints |
| [Deployment](docs/deployment.md) | Compose and HuggingFace container deployment |
| [Agent Design](docs/agent-design.md) | Current fixture-backed run model and future live-agent direction |
| [Data and Retrieval](docs/data-and-retrieval.md) | Target retrieval/data contracts for post-fixture work |
