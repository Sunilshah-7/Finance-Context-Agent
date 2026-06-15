# FinContext Agent

FinContext Agent V2 is a financial research prototype. It shows a visible agent workflow that explains disclosure-language changes in SEC filings and connects those changes to portfolio exposure with validated citations.

The current implementation is intentionally demo-reliable:

- Go backend for all live APIs and agent orchestration.
- Next.js analyst console exported as static assets.
- Curated JSON fixtures for portfolio, evidence, disclosure diffs, risk scores, memo, and metrics.
- No live EDGAR ingestion, Qdrant, SQLite, or Python in the request path.
- Python is reserved for future offline fixture generation and parsing experiments.

## Architecture

```text
Browser
  |
  v
Go service
  ├─ serves exported Next.js UI
  ├─ /api/health
  ├─ /api/demo/portfolio
  ├─ /api/agent-runs
  ├─ /api/diff
  ├─ /api/chat
  └─ fixture validation at startup
```

## Run Locally

Backend:

```bash
cd backend
go test ./...
FIXTURE_DIR=../data/fixtures go run ./cmd/fincontext
```

Frontend dev server:

```bash
cd apps/demo-ui
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 npm run dev
```

One-container deployment:

```bash
docker build -t fincontext-agent .
docker run --rm -p 7860:7860 fincontext-agent
```

Open `http://localhost:7860`.

## API

- `GET /api/health`
- `GET /api/demo/portfolio`
- `POST /api/agent-runs`
- `GET /api/agent-runs/{run_id}`
- `GET /api/agent-runs/{run_id}/events`
- `GET /api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025`
- `POST /api/chat`
- `GET /api/metrics`

All memo, chat, diff, and risk outputs must reference citation IDs known to the fixture store. The backend fails startup validation if fixtures contain unsupported citation references.
