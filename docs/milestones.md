# Milestones

## Day 1: Working Skeleton

- Create Next.js dashboard.
- Create Cloudflare Worker API.
- Define schemas and D1 migrations.
- Upload portfolio CSV to R2.
- Create holdings table.
- Stub AMD Agent API with FastAPI.

Deliverable:

- Portfolio upload appears in dashboard.

## Day 2: Ingestion and Retrieval

- Add ticker-to-CIK resolver.
- Fetch 10-K/10-Q documents.
- Parse HTML filings into markdown sections.
- Chunk filings with citation anchors.
- Generate embeddings.
- Store chunks in vector index.
- Build retrieval endpoint.

Deliverable:

- Ask questions over one ticker with citations.

## Day 3: Agents and Risk Scoring

- Implement LangGraph state.
- Add portfolio context, retrieval, diff, risk, memo, and verifier agents.
- Add structured outputs.
- Add score calculation.
- Persist findings.

Deliverable:

- Portfolio-aware memo with risk scores.

## Day 4: Cloudflare Integration

- Configure D1, R2, Queues, Vectorize.
- Wire Worker to AMD Agent API.
- Add streaming responses.
- Add auth/session basics.
- Add job status UI.

Deliverable:

- Public Cloudflare demo talks to AMD GPU backend.

## Day 5: Demo Polish and Benchmarks

- Add seed portfolio.
- Add disclosure diff viewer.
- Add benchmark panel.
- Run evals.
- Tighten citations and disclaimers.
- Record demo script.

Deliverable:

- Hackathon-ready demo and architecture presentation.

## Stretch

- Add PDF/table multimodal extraction.
- Add earnings transcript ingestion.
- Add alert emails.
- Add peer comparison.
- Add historical risk chart.

