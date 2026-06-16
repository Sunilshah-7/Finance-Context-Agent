# packages/schemas

This package is not part of the current runnable Go-first implementation. It is
reserved for future Python offline parsing, evaluation, or interoperability work.

`README.md` is the source of truth for the active service contracts. Current
runtime data types live in Go under `backend/internal/domain`.

## Current Contract Sources

- Go domain types: `backend/internal/domain/types.go`
- Agent API contracts: `docs/api-contracts.md`
- Fixture JSON shapes: `data/fixtures/*.json`

## Future Use

If Python ingestion or evaluation code needs shared Pydantic models, add them
here deliberately and keep them aligned with the Go contracts. Do not introduce
Python schemas as the canonical runtime contract while the Agent API and
Gateway are implemented in Go.

## Rules

- Do not define a second competing `AnalysisState` contract without coordinating
  with the Agent API owner.
- Do not point active service docs at `packages/schemas/python` unless those
  files exist and are used by the runnable code.
- Keep frontend TypeScript types aligned with the Agent API JSON responses.
