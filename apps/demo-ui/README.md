---
title: FinContext Agent
colorFrom: slate
colorTo: blue
sdk: gradio
sdk_version: 4.x
app_file: app.py
pinned: false
---

# FinContext Agent Demo UI

This directory contains the Gradio UI intended for HuggingFace Spaces. It is a
financial research console for SEC disclosure drift analysis, not a generic AI
landing page.

The UI calls only the Agent API. It does not call SQLite, Qdrant, the Inference
Gateway, vLLM, TEI, or EDGAR directly.

## What The UI Shows

| Tab | Purpose |
| --- | --- |
| Portfolio | Preview the seed portfolio and upload a CSV to Agent API |
| Analysis Run | Start an analysis job and refresh job status |
| Disclosure Drift | Load old-versus-new filing language changes by ticker and section |
| Evidence Explorer | Inspect indexed filing documents exposed by Agent API |
| Risk Scores | Show research risk scores from completed findings |
| Analyst Memo | Render memo text, evidence table, limitations, and disclaimer |
| AMD Benchmark | Show measured AMD VM metrics when the backend reports them |

## Design Direction

The visual style is inspired by the local prototype folder
`AMD Hack Financial Frontend Kinda/`, but that folder is intentionally ignored
and not shipped. The implemented product remains Gradio so it can deploy as a
HuggingFace Space and stay aligned with the repo architecture.

The UI uses:

- compact analyst-console layout;
- muted off-white surfaces and slate borders;
- evidence cards and citation chips;
- backend connected/offline states;
- tables for filings, risk scores, and benchmark metrics.

It does not use fake live benchmark numbers. If the backend is unavailable, the
UI shows offline states and the committed seed portfolio only.

## Environment Variables

```bash
AGENT_API_URL=http://localhost:8090
AGENT_API_KEY=your-api-key
PORT=7860
```

`AGENT_API_KEY` is optional for local offline preview, but required once the
Agent API enforces bearer-token authentication.

## Run Locally

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:7860
```

The app should still load if Agent API is not running. In that mode, only the
seed portfolio preview and empty/offline states are available.

## HuggingFace Spaces Deployment

Set Space secrets:

- `AGENT_API_URL`
- `AGENT_API_KEY`

Push this directory as the Space root:

```bash
git remote add space https://huggingface.co/spaces/{HF_USERNAME}/fincontext-agent
git subtree push --prefix apps/demo-ui space main
```

## Backend Contract

The UI follows `docs/api-contracts.md` and expects these Agent API endpoints:

- `GET /health`
- `POST /api/portfolio/upload`
- `POST /api/analyze`
- `GET /api/jobs/{job_id}`
- `GET /api/findings/{portfolio_id}`
- `GET /api/diff/{ticker}`
- `GET /api/documents/{ticker}`
- `GET /api/benchmark/metrics`

If an endpoint is missing or returns an error, the tab renders a clear failure
message instead of crashing.

## Compliance

The UI must not show buy, sell, hold, short, outperform, underperform, or other
investment recommendation language. The required disclaimer appears on every
page:

```text
This output is research assistance only and does not constitute investment advice.
```
