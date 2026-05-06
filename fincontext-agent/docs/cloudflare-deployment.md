# Deployment: HuggingFace Spaces + AMD Developer Cloud

This document replaces the previous Cloudflare deployment plan. The decision to drop Cloudflare is documented in `docs/architecture.md`.

## Summary

| Component | Where it runs | Technology |
|-----------|--------------|------------|
| Demo UI | HuggingFace Spaces | Gradio |
| Agent API | AMD Developer Cloud VM | FastAPI + LangGraph |
| Inference Gateway | AMD Developer Cloud VM | FastAPI proxy |
| vLLM (72B + 14B) | AMD Developer Cloud VM | Docker |
| Embedding + Reranker | AMD Developer Cloud VM | Docker (TEI) |
| Vector store | AMD Developer Cloud VM | Docker (Qdrant) |
| Metadata DB | AMD Developer Cloud VM | SQLite |

---

## AMD Developer Cloud VM Setup

### 1. Provision a VM

Log in to AMD Developer Cloud and provision an instance with:
- AMD Instinct GPU (MI300X preferred, MI250 acceptable)
- At least 64 GB system RAM
- At least 500 GB disk (for models + Qdrant data + EDGAR HTML cache)
- Ubuntu 22.04 LTS

### 2. Install ROCm

Follow AMD's official ROCm installation guide for Ubuntu 22.04. Verify:
```bash
rocm-smi
# Should show GPU device with full 192 GB VRAM for MI300X
```

### 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version  # verify
```

### 4. Configure Environment

```bash
cd fincontext-agent
cp configs/.env.example configs/.env
# Edit .env:
# - Set HF_TOKEN to your HuggingFace access token
# - Set VLLM_MODEL_ID to Qwen/Qwen2.5-72B-Instruct
# - Set VLLM_14B_MODEL_ID to Qwen/Qwen2.5-14B-Instruct
# - Set SEC_USER_AGENT to FinContextAgent/0.1 your-email@example.com
# - Set AGENT_API_KEY to a strong random string
```

### 5. Start All Services

```bash
cd fincontext-agent/infra/amd-gpu
docker compose up -d

# Monitor model load progress (72B takes 3-5 minutes to load)
docker compose logs -f vllm-72b

# Verify all services healthy
curl http://localhost:8000/health    # vLLM 72B
curl http://localhost:8001/health    # vLLM 14B
curl http://localhost:8002/health    # embedding
curl http://localhost:8003/health    # reranker
curl http://localhost:6333/healthz   # Qdrant
```

### 6. Initialize Database and Collection

```bash
cd fincontext-agent
sqlite3 fincontext.db < infra/schema.sql

# Create Qdrant collection
python -c "
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
c = QdrantClient('http://localhost:6333')
c.create_collection('fincontext_chunks', vectors_config=VectorParams(size=1024, distance=Distance.COSINE))
c.create_payload_index('fincontext_chunks', 'ticker', 'keyword')
c.create_payload_index('fincontext_chunks', 'filing_type', 'keyword')
c.create_payload_index('fincontext_chunks', 'filed_at', 'keyword')
print('Collection created')
"
```

### 7. Run Pre-Ingestion

```bash
cd fincontext-agent/services/ingestion-worker
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

### 8. Start Inference Gateway and Agent API

```bash
# Terminal 1: Inference Gateway
cd fincontext-agent/services/inference-gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 2: Agent API
cd fincontext-agent/services/agent-api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090

# Verify Agent API is healthy
curl http://localhost:8090/health
```

### 9. Expose Agent API Externally

The Gradio app on HuggingFace Spaces needs to reach the Agent API. Options:

**Option A: AMD VM public IP with firewall rule (preferred)**
- Open port 8090 in the AMD cloud firewall/security group
- Set `AMD_VM_PUBLIC_IP` in the Gradio app's HuggingFace Space secrets
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

**Option B: Cloudflare Tunnel (fallback if direct exposure fails)**
```bash
# Install cloudflared on AMD VM
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
# Create a tunnel (does not require Cloudflare account for quick tunnels)
./cloudflared tunnel --url http://localhost:8090
# Cloudflare prints a public HTTPS URL — use this as AGENT_API_URL in Gradio
```

**Option C: ngrok (simplest fallback)**
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
git subtree push --prefix fincontext-agent/apps/demo-ui space main
```

Alternatively, maintain `apps/demo-ui/` as a separate git repo and push directly:
```bash
cd fincontext-agent/apps/demo-ui
git init
git remote add origin https://huggingface.co/spaces/{HF_USERNAME}/fincontext-agent
git add .
git commit -m "Initial Gradio app"
git push origin main
```

### 4. HuggingFace Space README (required)

The Space's `README.md` is shown on the Space page. It must explain the AMD hardware story for judges:

```markdown
---
title: FinContext Agent
emoji: 📊
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
Gradio (HuggingFace Spaces)
    ↓ HTTPS
AMD Developer Cloud VM
  ├── FastAPI Agent API (LangGraph)
  ├── Inference Gateway (vLLM proxy)
  ├── Qwen2.5-72B via vLLM/ROCm
  ├── Qwen2.5-14B via vLLM/ROCm
  ├── BGE embeddings + reranker via TEI
  └── Qdrant vector store
```
```

### 5. Verify Deployment

After pushing, wait ~2 minutes for the Space to build. Then:
1. Open the Space URL (shown in HuggingFace after deployment)
2. Confirm the Gradio UI loads
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

The AMD benchmark panel in the Gradio UI shows real-time tokens/sec, GPU memory utilization, and per-request latency collected by the Inference Gateway.

---

## Cost Management ($100 AMD Credit)

Estimated GPU costs:
- MI300X: approximately $1.99–$3.00/hour depending on AMD Developer Cloud pricing tier
- $100 credit = approximately 33–50 hours of GPU time

Usage breakdown:
- Pre-ingestion (embedding 15,000 chunks): ~30 minutes of GPU time
- Development + debugging (running the graph ~50 times): ~3–4 hours
- Demo sessions (20 end-to-end runs): ~2 hours
- **Total estimated: 6–8 GPU hours out of 33–50 available**

To protect the credit:
- Shut down vLLM containers when not actively developing
- Use `docker compose stop vllm-72b vllm-14b` and restart when needed
- The 72B model takes 3-5 minutes to reload — plan for this in your workflow
- Do NOT leave the AMD VM running overnight with vLLM active unless intentionally benchmarking

---

## Sharing Pre-Ingested Data Between Teammates

After running ingestion on the AMD VM, create a shareable snapshot:

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
