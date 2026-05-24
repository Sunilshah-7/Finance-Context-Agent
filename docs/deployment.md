# Deployment: HuggingFace Spaces + NVIDIA NIM

<<<<<<< HEAD
This document describes the current deployment architecture: a HuggingFace Static Space React UI connected to the Agent API running on AMD Developer Cloud.
=======
This is the prototype deployment plan. The app does not require an AMD GPU VM or
local 70B model serving. LLM calls go through NVIDIA NIM via the Inference
Gateway; the backend host runs the application services, Qdrant, and SQLite.
>>>>>>> origin/dev

## Components

| Component | Where it runs | Technology |
|-----------|--------------|------------|
<<<<<<< HEAD
| Demo UI | HuggingFace Spaces | Vite React static app |
| Agent API | AMD Developer Cloud VM | FastAPI + LangGraph |
| Inference Gateway | AMD Developer Cloud VM | FastAPI proxy |
| vLLM (72B + 14B) | AMD Developer Cloud VM | Docker |
| Embedding + Reranker | AMD Developer Cloud VM | Docker (TEI) |
| Vector store | AMD Developer Cloud VM | Docker (Qdrant) |
| Metadata DB | AMD Developer Cloud VM | SQLite |
=======
| Demo UI | HuggingFace Spaces | Vite React Static Space |
| Agent API | Backend host | FastAPI + LangGraph |
| Inference Gateway | Backend host | FastAPI proxy to NIM and retrieval backends |
| LLM inference | NVIDIA NIM | OpenAI-compatible chat completions |
| Vector store | Backend host | Qdrant Docker container |
| Metadata DB | Backend host | SQLite |
>>>>>>> origin/dev

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

<<<<<<< HEAD
The React app on HuggingFace Spaces needs to reach the Agent API. Options:

**Option A: AMD VM public IP with firewall rule (preferred)**
- Open port 8090 in the AMD cloud firewall/security group
- Set `AGENT_API_URL` in the React app's HuggingFace Space variables
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
# ngrok prints a public HTTPS URL — use this as AGENT_API_URL in React
```

---

## HuggingFace Spaces Deployment

### 1. Create the Space

```bash
pip install huggingface_hub
huggingface-cli login  # enter your HF token

# Create a new Static Space
huggingface-cli repo create fincontext-agent --type space --space-sdk static
```

### 2. Set Space Secrets

In HuggingFace Space settings → Secrets, add:
```
AGENT_API_URL = https://your-amd-vm-ip:8090   (or tunnel URL)
```

Static browser apps cannot keep secrets. Do not put `AGENT_API_KEY` in the React frontend; the Agent API must expose demo-safe public endpoints with CORS and rate limiting.

### 3. Deploy the React Static App

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
git commit -m "Initial React app"
git push origin main
```

### 4. HuggingFace Space README (required)

The Space's `README.md` is shown on the Space page. It must explain the AMD hardware story for judges:

```markdown
---
title: FinContext Agent
colorFrom: blue
colorTo: indigo
=======
## HuggingFace Static Space

The Space repository should use `apps/demo-ui/` as its root.

```yaml
---
title: FinContext Agent
colorFrom: slate
colorTo: blue
>>>>>>> origin/dev
sdk: static
app_build_command: npm run build
app_file: dist/index.html
pinned: false
---
<<<<<<< HEAD

# FinContext Agent

Portfolio-aware financial intelligence platform built for the AMD Developer Hackathon 2026.

## What it does

Analyzes SEC filings (10-K and 10-Q) for your stock portfolio using a 4-agent LangGraph workflow:
detects material disclosure changes year-over-year, scores holding-level risk, and generates
citation-grounded analyst memos.

## AMD Hardware

The inference backend runs on AMD Developer Cloud with AMD Instinct MI300X (192 GB HBM3 VRAM).

Key AMD advantage: Qwen2.5-72B runs in FP16 on a **single** MI300X with full 65,536-token
context window. This allows processing an entire 10-K annual report in one pass with no context
fragmentation. NVIDIA H100 (80 GB) cannot hold a 72B FP16 model without multi-GPU setup.

## HuggingFace Models Used

- `Qwen/Qwen2.5-72B-Instruct` — analyst memo generation
- `Qwen/Qwen2.5-14B-Instruct` — retrieval planning, disclosure classification
- `BAAI/bge-large-en-v1.5` — document embeddings
- `BAAI/bge-reranker-large` — evidence reranking

## Architecture

```
React Static Space (HuggingFace Spaces)
    ↓ HTTPS
AMD Developer Cloud VM
  ├── FastAPI Agent API (LangGraph)
  ├── Inference Gateway (vLLM proxy)
  ├── Qwen2.5-72B via vLLM/ROCm
  ├── Qwen2.5-14B via vLLM/ROCm
  ├── BGE embeddings + reranker via TEI
  └── Qdrant vector store
```
=======
>>>>>>> origin/dev
```

Configure the public Agent API URL for the frontend:

<<<<<<< HEAD
After pushing, wait ~2 minutes for the Space to build. Then:
1. Open the Space URL (shown in HuggingFace after deployment)
2. Confirm the React UI loads
3. Upload the seed portfolio CSV (`demo/seed_portfolio.csv`)
4. Click "Analyze" and verify the job starts (requires AMD VM to be running and reachable)

---

## Monitoring (Minimal)

For the hackathon, monitoring is minimal:

```bash
# Check GPU memory usage
watch -n 5 rocm-smi

# Check running containers
docker compose ps

# Check Agent API logs
uvicorn logs or journalctl -u fincontext-agent-api -f

# Check Qdrant storage
curl http://localhost:6333/collections/fincontext_chunks
```

The AMD benchmark panel in the React UI shows real-time tokens/sec, GPU memory utilization, and per-request latency collected by the Inference Gateway.
=======
```text
AGENT_API_URL=https://your-agent-api-url
```

Static browser apps cannot keep secrets. Do not embed `AGENT_API_KEY` in the
React frontend; use demo-safe public endpoints, CORS, and rate limiting on the
Agent API.
>>>>>>> origin/dev

## Inference Operations

NIM is the only chat-completions backend for the prototype:

- `fincontext-planner` routes to `NIM_PLANNER_MODEL`.
- `fincontext-reasoner` routes to `NIM_REASONER_MODEL`.
- `NIM_API_KEY` must be configured on the backend host.
- Gateway metrics are the source for latency, token throughput, provider status,
  and request counts.

This avoids local 70B infrastructure while preserving a clean provider boundary.
