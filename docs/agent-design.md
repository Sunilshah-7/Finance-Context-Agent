# Agent Design

`README.md` is the source of truth. The current implementation is
fixture-backed Go orchestration, not a live LangGraph graph. This document
records what exists now and how it maps to the target agent workflow.

## Current Implementation

Implementation: `backend/internal/agent/runner.go`

The Agent API creates a run with five visible stages:

1. `portfolio_context`
2. `evidence_retrieval`
3. `disclosure_diff`
4. `risk_scoring`
5. `memo_generation`

The runner simulates stage progress, validates the curated memo citations, and
then attaches fixture evidence, disclosure changes, risk scores, memo, and
metrics to the completed run.

This gives the demo the product shape of the target workflow while avoiding
live EDGAR/retrieval/model dependence during early integration.

## Current Data Flow

```text
POST /api/agent-runs
  -> create AgentRun with queued stages
  -> persist run to SQLite
  -> background goroutine advances stage statuses
  -> validate fixture memo citation ids
  -> attach fixture evidence, changes, risk scores, memo, metrics
  -> persist completed run
```

## Citation Discipline

Implementation: `backend/internal/citations/validator.go`

- Every evidence fixture has a stable `id`.
- The fixture store indexes evidence by id at startup.
- Disclosure changes, risk drivers, memo changes, and memo evidence tables must
  reference known citation ids.
- Chat answers also request known citation ids before returning citations.

This citation validator is implemented now and should remain in place when live
retrieval replaces fixture data.

## Target Workflow

The product target is still the 4-step analysis workflow described in the
README:

1. Portfolio context and retrieval planning.
2. Filing retrieval with BM25, Qdrant vector search, RRF, reranking, and section
   diversity.
3. Disclosure-change classification across filing periods.
4. Analyst memo generation with citation verification and hardcoded research
   disclaimer.

Those steps are future implementation work in the current Go-first codebase.
When they are built, they should either extend the Go runner or be introduced
behind the existing Agent API contract without adding a second public Agent API.

## Target Model Usage

- `fincontext-planner`: planning, retrieval-oriented structured output, and
  intermediate classification.
- `fincontext-reasoner`: final memo generation.
- Embeddings and reranking go through the Inference Gateway, never directly from
  Agent API code to backend-specific services.

## Non-Goals

- Do not add nine separate agents.
- Do not add buy/sell/hold recommendations.
- Do not bypass the Gateway for NVIDIA NIM, embeddings, or reranking.
- Do not add another frontend app.
