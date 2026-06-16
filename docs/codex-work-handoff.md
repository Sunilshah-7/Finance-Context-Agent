# Codex Work Handoff

`README.md` is the source of truth. This handoff summarizes the current
repository state rather than older PR-by-PR history.

## Current Implemented Shape

- Go Agent API in `backend/cmd/agent-api`.
- Go Inference Gateway in `backend/cmd/inference-gateway`.
- Next.js demo UI in `apps/demo-ui`.
- Docker Compose stack in `infra/docker-compose.yml`.
- HuggingFace-ready root `Dockerfile`.
- Curated fixture data in `data/fixtures`.
- SQLite run/fixture metadata persistence.
- Qdrant health and collection initialization.

## Current Demo Mode

The demo is fixture-backed. The Agent API simulates staged analysis progress,
validates fixture citations, and returns curated evidence, disclosure changes,
risk scores, memo, chat answers, and metrics.

This is intentional until live EDGAR ingestion, embedding, reranking, retrieval,
and generated memo output are connected.

## Safe Follow-Up Work

- Documentation cleanup aligned to `README.md`.
- UI polish that preserves current API calls.
- Gateway metrics improvements.
- Agent API persistence and response-contract tests.
- Ingestion design docs and future implementation behind existing contracts.

## Coordinate Before Changing

- `backend/internal/domain/types.go`
- Agent API response shapes.
- Qdrant payload schema.
- SQLite schema beyond the current Go-initialized tables.
- Any work that replaces fixture mode with live retrieval.

## Things Not To Reintroduce

- A Python/FastAPI Agent API as a second service.
- A Python/FastAPI Gateway as a second service.
- Vite-specific UI docs; the current UI is Next.js.
- Claims that live ingestion or live retrieval is already wired into the current
  run path.
