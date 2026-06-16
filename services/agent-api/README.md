# Agent API

This service is implemented in Go under `backend/cmd/agent-api`. The
`services/agent-api/` directory remains as a documentation placeholder from the
earlier Python plan; do not add a second Agent API here unless the team makes an
explicit architecture decision.

`README.md` is the source of truth for the runnable architecture.

## Current Responsibilities

- Serves the exported Next.js UI when `STATIC_DIR` is configured.
- Exposes the public demo API on port `8090`.
- Loads curated JSON fixtures from `FIXTURE_DIR`.
- Orchestrates fixture-backed agent runs with staged progress.
- Validates memo/chat citation IDs against loaded evidence fixtures.
- Persists agent runs, seeded portfolio data, and seeded citation data in SQLite.
- Checks and initializes the Qdrant `fincontext_chunks` collection.
- Checks Inference Gateway health through `INFERENCE_GATEWAY_URL`.

## Current Endpoints

- `GET /api/health`
- `GET /api/demo/portfolio`
- `POST /api/agent-runs`
- `GET /api/agent-runs/{run_id}`
- `GET /api/agent-runs/{run_id}/events`
- `GET /api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025`
- `POST /api/chat`
- `GET /api/metrics`

## Local Run

From the repository root:

```bash
cd backend
FIXTURE_DIR=../data/fixtures \
SQLITE_DB_PATH=../fincontext.db \
QDRANT_URL=http://localhost:6333 \
INFERENCE_GATEWAY_URL=http://localhost:8080 \
go run ./cmd/agent-api
```

Run tests:

```bash
cd backend
GOCACHE=/absolute/path/to/.gocache GOMODCACHE=/absolute/path/to/.gomodcache go test ./...
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8090` | Agent API listen port |
| `FIXTURE_DIR` | `data/fixtures` | Curated fixture JSON directory |
| `STATIC_DIR` | empty | Exported UI directory to serve |
| `SQLITE_DB_PATH` | `fincontext.db` | SQLite run/fixture metadata path |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST URL |
| `QDRANT_COLLECTION` | `fincontext_chunks` | Qdrant collection name |
| `QDRANT_VECTOR_SIZE` | `1024` | Qdrant vector size |
| `INFERENCE_GATEWAY_URL` | `http://localhost:8080` | Gateway base URL |
| `STRICT_DEPENDENCIES` | `false` | Exit on dependency setup failure when true |

## Still To Build

- Live EDGAR ingestion-backed retrieval instead of curated fixtures.
- Agent nodes that use retrieved chunks instead of fixture evidence.
- Auth, rate limiting, tenant/user model, and production observability.
