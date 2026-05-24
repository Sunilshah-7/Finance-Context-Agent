# Deployment: HuggingFace Spaces + NVIDIA NIM

This is the prototype deployment plan. The app does not require an AMD GPU VM or
local 70B model serving. LLM calls go through NVIDIA NIM via the Inference
Gateway; the backend host runs the application services, Qdrant, and SQLite.

## Components

| Component | Where it runs | Technology |
|-----------|--------------|------------|
| Demo UI | HuggingFace Spaces | Vite React Static Space |
| Agent API | Backend host | FastAPI + LangGraph |
| Inference Gateway | Backend host | FastAPI proxy to NIM and retrieval backends |
| LLM inference | NVIDIA NIM | OpenAI-compatible chat completions |
| Vector store | Backend host | Qdrant Docker container |
| Metadata DB | Backend host | SQLite |

## Backend Setup

```bash
cp configs/.env.example .env
# Set NIM_API_KEY, NIM_BASE_URL, SEC_USER_AGENT, and AGENT_API_KEY.

docker compose -f infra/docker-compose.yml up -d qdrant
sqlite3 fincontext.db < infra/schema.sql
python3 infra/qdrant/init_collection.py
```

Start the services:

```bash
cd services/inference-gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

cd ../agent-api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090
```

Only the Agent API should be publicly reachable. Keep Qdrant, SQLite, the
Gateway, embedding, and reranker services private to the backend host.

## HuggingFace Static Space

The Space repository should use `apps/demo-ui/` as its root.

```yaml
---
title: FinContext Agent
colorFrom: slate
colorTo: blue
sdk: static
app_build_command: npm run build
app_file: dist/index.html
pinned: false
---
```

Configure the public Agent API URL for the frontend:

```text
AGENT_API_URL=https://your-agent-api-url
```

Static browser apps cannot keep secrets. Do not embed `AGENT_API_KEY` in the
React frontend; use demo-safe public endpoints, CORS, and rate limiting on the
Agent API.

## Inference Operations

NIM is the only chat-completions backend for the prototype:

- `fincontext-planner` routes to `NIM_PLANNER_MODEL`.
- `fincontext-reasoner` routes to `NIM_REASONER_MODEL`.
- `NIM_API_KEY` must be configured on the backend host.
- Gateway metrics are the source for latency, token throughput, provider status,
  and request counts.

This avoids local 70B infrastructure while preserving a clean provider boundary.
