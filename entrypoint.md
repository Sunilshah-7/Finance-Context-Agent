# FinContext Agent

Portfolio-aware financial intelligence platform for Track 1: AI Agents & Agentic Workflows.

FinContext Agent ingests SEC filings, earnings transcripts, investor presentations, and financial reports, then connects document-level changes to a user portfolio. It produces citation-backed answers, disclosure-change alerts, risk scores, and analyst-style portfolio impact memos.

## Why This Project Fits AMD

The core workload is large-context, high-throughput financial document reasoning. AMD Instinct GPUs on AMD Developer Cloud are used for:

- Long-context LLM serving with vLLM on ROCm.
- Batch parsing and summarization across 10-K, 10-Q, 8-K, transcript, and PDF corpora.
- Embedding generation and reranking for retrieval.
- Multi-agent reasoning pipelines that evaluate risk, exposure, and filing changes in parallel.
- Benchmarks that compare latency, tokens/sec, cost per analyzed filing, and concurrent portfolio runs.

## Recommended Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui, Recharts.
- Edge/API: Cloudflare Pages, Workers, Queues, D1, R2, Vectorize, Workers KV, AI Gateway.
- Agent backend: Python, FastAPI, LangGraph, LlamaIndex, Pydantic, Celery or Dramatiq.
- GPU inference: AMD Developer Cloud, ROCm, vLLM OpenAI-compatible server.
- Models: Qwen2.5/3, Llama 3.1/3.3, Mistral, FinGPT/finance-tuned variants when licensing allows.
- Retrieval: BGE or E5 embeddings, BGE reranker, hybrid BM25/vector retrieval.
- Data: SEC EDGAR APIs, company filings, earnings call transcripts, portfolio CSV/broker export.
- Storage: Cloudflare R2 for source documents, D1 for app metadata, Vectorize for demo vector search, Postgres/pgvector for production option.
- Observability: OpenTelemetry, Cloudflare Analytics, LangSmith-compatible traces or OpenLLMetry.

## Document Map

- [Product and Scope](docs/product-scope.md)
- [Architecture](docs/architecture.md)
- [Component Build Plan](docs/component-build-plan.md)
- [Agent Design](docs/agent-design.md)
- [Data and Retrieval](docs/data-and-retrieval.md)
- [Risk Scoring](docs/risk-scoring.md)
- [AMD GPU Plan](docs/amd-gpu-plan.md)
- [Cloudflare Deployment](docs/cloudflare-deployment.md)
- [API Contracts](docs/api-contracts.md)
- [Security and Compliance](docs/security-compliance.md)
- [Demo Plan](docs/demo-plan.md)
- [Milestones](docs/milestones.md)
- [References](docs/references.md)

## Proposed Repository Layout

```text
fincontext-agent/
  apps/
    web/                       # Next.js UI deployed to Cloudflare Pages
    worker-api/                # Cloudflare Worker API gateway
  services/
    agent-api/                 # FastAPI + LangGraph orchestration on AMD cloud
    ingestion-worker/          # Filing ingestion, parsing, chunking, OCR/table extraction
    inference-gateway/         # OpenAI-compatible proxy to vLLM and reranker services
  packages/
    schemas/                   # Shared Pydantic/TypeScript schemas
    evals/                     # Retrieval, citation, risk-score, latency evals
  infra/
    amd-gpu/                   # ROCm/vLLM deployment assets
    cloudflare/                # Wrangler configs, D1 migrations, R2/Queue bindings
  configs/
    .env.example
  docs/
```

This repository currently contains the planning package and starter config templates. The layout above is the target implementation structure for the hackathon build.
