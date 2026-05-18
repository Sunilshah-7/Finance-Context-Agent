# Deployment: HuggingFace Spaces + NVIDIA NIM

This document describes the current deployment architecture: a HuggingFace Spaces Gradio UI connected to the Agent API, with LLM inference routed through NVIDIA NIM by the Inference Gateway.

## Summary

| Component | Where it runs | Technology |
|-----------|--------------|------------|
| Demo UI | HuggingFace Spaces | Gradio |
| Agent API | Backend host | FastAPI + LangGraph |
| Inference Gateway | Backend host | FastAPI proxy |
| LLM inference | NVIDIA NIM hosted endpoints | OpenAI-compatible chat completions |
| Embedding + Reranker | Backend host | Local retrieval services |
| Vector store | Backend host | Docker (Qdrant) |
| Metadata DB | Backend host | SQLite |

---

## Backend Host Setup

### 1. Provision a Host

Provision an instance with:
- At least 16 GB system RAM
- At least 100 GB disk for Qdrant data, SQLite, logs, and EDGAR HTML cache
- Ubuntu 22.04 LTS

No local GPU runtime is required for the NIM-hosted MVP.

### 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version  # verify
```

### 3. Configure Environment

```bash
# From repo root
cp configs/.env.example .env
# Edit .env:
# - Set NIM_API_KEY to your NVIDIA NIM API key
# - Set NIM_BASE_URL to the NIM OpenAI-compatible base URL
# - Set NIM_REASONER_MODEL and NIM_PLANNER_MODEL
# - Set SEC_USER_AGENT to FinContextAgent/0.1 your-email@example.com
# - Set AGENT_API_KEY to a strong random string
```

### 4. Start Storage Services

```bash
docker compose -f infra/amd-gpu/docker-compose.yml up -d qdrant

curl http://localhost:6333/healthz   # Qdrant
```

### 5. Initialize Database and Collection

```bash
# From repo root
sqlite3 fincontext.db < infra/schema.sql

# Create Qdrant collection
python3 infra/qdrant/init_collection.py
```

### 6. Run Pre-Ingestion

```bash
cd services/ingestion-worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python ingest.py \
  --tickers AMD,NVDA,MSFT,JPM,TSLA \
  --filing-types 10-K,10-Q \
  --years 4 \
  --db-path ../../fincontext.db \
  --qdrant-url http://localhost:6333 \
  --gateway-url http://localhost:8080

# Verify ingestion
sqlite3 ../../fincontext.db "SELECT ticker, count(*) FROM chunks GROUP BY ticker;"
```

### 7. Start Inference Gateway and Agent API

```bash
# Terminal 1: Inference Gateway
cd services/inference-gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 2: Agent API
cd services/agent-api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090

# Verify Agent API is healthy
curl http://localhost:8090/health
```

### 8. Expose Agent API Externally

The Gradio app on HuggingFace Spaces needs to reach the Agent API. Options:

**Option A: Backend public URL with firewall rule (preferred)**
- Open port 8090 in the cloud firewall/security group
- Set `AGENT_API_URL` in the Gradio app's HuggingFace Space secrets
- Use HTTPS via an nginx reverse proxy with a self-signed cert (or Let's Encrypt if you have a domain)

```nginx
# /etc/nginx/sites-available/fincontext
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

**Option B: ngrok fallback**
```bash
ngrok http 8090
# ngrok prints a public HTTPS URL — use this as AGENT_API_URL in Gradio
```

---

## HuggingFace Spaces Deployment

### 1. Create the Space

```bash
pip install huggingface_hub
huggingface-cli login  # enter your HF token

# Create a new Gradio Space
huggingface-cli repo create fincontext-agent --type space --space-sdk gradio
```

### 2. Set Space Secrets

In HuggingFace Space settings → Secrets, add:
```
AGENT_API_URL = https://your-amd-vm-ip:8090   (or tunnel URL)
AGENT_API_KEY = your-strong-api-key
```

These are available as environment variables in the Gradio app at runtime.

### 3. Deploy the Gradio App

The Space repository needs the files from `apps/demo-ui/` at its root.

Using git subtree push (recommended):
```bash
# Add the Space as a remote
git remote add space https://huggingface.co/spaces/{HF_USERNAME}/fincontext-agent

# Push only the demo-ui subdirectory as the Space root
git subtree push --prefix apps/demo-ui space main
```

Alternatively, maintain `apps/demo-ui/` as a separate git repo and push directly:
```bash
cd apps/demo-ui
git init
git remote add origin https://huggingface.co/spaces/{HF_USERNAME}/fincontext-agent
git add .
git commit -m "Initial Gradio app"
git push origin main
```

### 4. HuggingFace Space README (required)

The Space's `README.md` is shown on the Space page. It must explain the current NVIDIA NIM inference architecture:

```markdown
---
title: FinContext Agent
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.x
app_file: app.py
pinned: false
---

# FinContext Agent

Portfolio-aware financial intelligence platform built for the AMD Developer Hackathon 2026.

## What it does

Analyzes SEC filings (10-K and 10-Q) for your stock portfolio using a 4-agent LangGraph workflow:
detects material disclosure changes year-over-year, scores holding-level risk, and generates
citation-grounded analyst memos.

## Inference

The live MVP routes LLM calls through NVIDIA NIM hosted inference endpoints using an
OpenAI-compatible Inference Gateway. This keeps the Agent API and ingestion worker independent
from the serving backend.

## HuggingFace Models Used

- `Qwen/Qwen2.5-72B-Instruct` — analyst memo generation
- `Qwen/Qwen2.5-7B-Instruct` — retrieval planning, disclosure classification
- Local embedding model — document embeddings
- Local reranking/scoring — evidence reranking

## Architecture

```
Gradio (HuggingFace Spaces)
    ↓ HTTPS
Backend host
  ├── FastAPI Agent API (LangGraph)
  ├── Inference Gateway
  ├── NVIDIA NIM hosted chat completions
  ├── Local embeddings + reranker
  └── Qdrant vector store
```
```

### 5. Verify Deployment

After pushing, wait ~2 minutes for the Space to build. Then:
1. Open the Space URL (shown in HuggingFace after deployment)
2. Confirm the Gradio UI loads
3. Upload the seed portfolio CSV (`demo/seed_portfolio.csv`)
4. Click "Analyze" and verify the job starts (requires the backend and NIM credentials to be configured)

---

## Monitoring (Minimal)

For the hackathon, monitoring is minimal:

```bash
# Check running containers
docker compose -f infra/amd-gpu/docker-compose.yml ps

# Check Agent API logs
uvicorn logs or journalctl -u fincontext-agent-api -f

# Check Qdrant storage
curl http://localhost:6333/collections/fincontext_chunks
```

The inference metrics panel in the Gradio UI shows tokens/sec, per-request latency, provider/model labels, and recent request counts collected by the Inference Gateway.

---

## Cost Management

Hosted inference costs depend on the NVIDIA NIM endpoint, model, and usage tier. Track usage through Gateway metrics and the provider dashboard.

Usage breakdown:
- Pre-ingestion embeddings: local CPU/runtime cost
- Development + debugging: NIM chat completion calls
- Demo sessions: NIM chat completion calls plus local retrieval

To protect the budget:
- Use the planner model for intermediate calls.
- Use the reasoner model only for final memo generation.
- Cache or snapshot demo results for rehearsal.
- Do not run repeated end-to-end analyses when a focused mocked test is enough.

---

## Sharing Pre-Ingested Data Between Teammates

After running ingestion on the backend host, create a shareable snapshot:

```bash
# Qdrant snapshot
curl -X POST "http://localhost:6333/collections/fincontext_chunks/snapshots"
# Returns a snapshot filename — download it
curl "http://localhost:6333/collections/fincontext_chunks/snapshots/{snapshot_name}" \
  -o fincontext_chunks_snapshot.tar

# SQLite backup
cp fincontext.db fincontext_demo.db
```

Share both files with your teammate. They restore with:
```bash
# Restore Qdrant
curl -X POST "http://localhost:6333/collections/fincontext_chunks/snapshots/upload" \
  -F "snapshot=@fincontext_chunks_snapshot.tar"

# Restore SQLite
cp fincontext_demo.db fincontext.db
```

Both teammates working from the same snapshot ensures identical retrieval results and prevents "it works on my machine" demo surprises.
