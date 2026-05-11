# AMD VM Ingestion Smoke Playbook

This playbook is the Day 1/Day 2 checklist for proving that the AMD VM can
support real ingestion data. It does not change application code. It explains
the exact order to bring up storage/model services, run one AMD filing through
the ingestion worker, validate the output, and send Kishan the data he needs for
retrieval and reranking work.

Use this before full demo ingestion. Do not live-ingest during the judge demo.

## Goal

By the end of this smoke test, the team should know whether:

- the AMD VM can see the GPU;
- Docker services for vLLM, TEI, and Qdrant are up;
- the Inference Gateway can reach embeddings and reranker backends;
- SQLite schema was applied successfully;
- Qdrant collection `fincontext_chunks` exists;
- one AMD 10-K ingestion writes chunks to SQLite and vectors to Qdrant;
- citation anchors follow the exact required format;
- Kishan has enough sample output to start retrieval/reranker/UI citation-card
  wiring.

## What This Does Not Prove

This smoke test does not prove the full product is demo-ready. It is only the
first real data-path check.

It does not prove:

- full AMD/NVDA/MSFT/JPM/TSLA demo corpus quality;
- disclosure-change classification quality;
- final memo quality;
- React UI integration;
- public HTTPS access from HuggingFace Spaces;
- benchmark numbers.

Those come later.

## Required Repo State

Run this from a branch that includes these merged PRs:

- PR #17: ingestion worker foundation;
- PR #18: demo data backup/snapshot ops;
- PR #20: Inference Gateway foundation;
- PR #22: ingestion validation helpers.

Recommended extra PR before using the shorter validation command:

- PR #24: ingestion validation CLI.

If PR #24 is not merged yet, use the fallback Python snippet in the validation
section.

## 1. Create The Real `.env`

From the repository root on the AMD VM:

```bash
cp configs/.env.example .env
```

Edit `.env` and set real values:

```bash
AMD_VM_PUBLIC_IP=<vm-public-ip>
HF_TOKEN=<real-huggingface-token>
AGENT_API_KEY=<strong-random-string>
SEC_USER_AGENT=FinContextAgent/0.1 <real-email-address>
MODEL_CACHE_DIR=/models
HF_HOME=/models/huggingface
SQLITE_DB_PATH=./fincontext.db
QDRANT_COLLECTION=fincontext_chunks
```

Do not commit `.env`.

Quick sanity check:

```bash
test -n "$HF_TOKEN"
test -n "$SEC_USER_AGENT"
```

If those fail, source the file in the current shell:

```bash
set -a
source .env
set +a
```

## 2. Verify AMD GPU Visibility

Run:

```bash
rocm-smi
```

Pass condition:

- at least one AMD GPU is listed;
- memory and utilization fields are visible;
- command exits successfully.

Fail condition:

- command not found;
- no GPU listed;
- permission errors accessing `/dev/kfd` or `/dev/dri`.

If this fails, stop. Do not start model containers until ROCm/GPU visibility is
fixed.

## 3. Start Docker Services

From repository root:

```bash
docker compose --env-file .env -f infra/amd-gpu/docker-compose.yml up -d
```

Check containers:

```bash
docker compose --env-file .env -f infra/amd-gpu/docker-compose.yml ps
```

Expected services:

```text
vllm-72b
vllm-14b
tei-embedding
tei-reranker
qdrant
```

The 72B service can take several minutes to load. Watch logs if needed:

```bash
docker logs -f fincontext-vllm-72b
docker logs -f fincontext-vllm-14b
docker logs -f fincontext-tei-embedding
docker logs -f fincontext-tei-reranker
docker logs -f fincontext-qdrant
```

Pass condition:

- Qdrant is healthy;
- TEI embedding and reranker services are healthy;
- vLLM 14B is healthy;
- vLLM 72B is healthy or still loading with normal model-load logs.

## 4. Start The Inference Gateway

From repository root:

```bash
cd services/inference-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
set -a
source ../../.env
set +a
uvicorn main:app --host 0.0.0.0 --port 8080
```

In another shell, check:

```bash
curl -s http://localhost:8080/health
```

Pass condition:

- Gateway responds with JSON;
- embedding and reranker services are not missing;
- model services are either ready or clearly reported as loading/degraded.

For the one-filing ingestion smoke, the critical route is embeddings:

```bash
curl -s http://localhost:8080/health | python3 -m json.tool
```

If the embedding backend is down, stop. Ingestion cannot write vectors without
Gateway `/v1/embeddings`.

## 5. Initialize SQLite

From repository root:

```bash
sqlite3 fincontext.db < infra/schema.sql
```

Verify tables:

```bash
sqlite3 fincontext.db ".tables"
```

Expected tables include:

```text
documents
chunks
chunks_fts
analysis_jobs
findings
```

Pass condition:

- command exits successfully;
- `.tables` shows `documents`, `chunks`, and `chunks_fts`.

Do not commit `fincontext.db`.

## 6. Initialize Qdrant Collection

From repository root:

```bash
python3 infra/qdrant/init_collection.py \
  --qdrant-url http://localhost:6333 \
  --collection fincontext_chunks
```

If intentionally resetting the collection before loading demo data:

```bash
python3 infra/qdrant/init_collection.py \
  --qdrant-url http://localhost:6333 \
  --collection fincontext_chunks \
  --recreate
```

Use `--recreate` only when everyone agrees it is safe to delete old points.

Verify collection:

```bash
curl -s http://localhost:6333/collections/fincontext_chunks | python3 -m json.tool
```

Pass condition:

- collection exists;
- vector size is 1024;
- distance is cosine;
- payload indexes include ticker, filing type, filed date, and section.

## 7. Run One AMD 10-K Ingestion

From repository root:

```bash
cd services/ingestion-worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../../packages/schemas
set -a
source ../../.env
set +a

python3 ingest.py \
  --tickers AMD \
  --filing-types 10-K \
  --years 1 \
  --db-path ../../fincontext.db \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks \
  --gateway-url http://localhost:8080
```

Pass condition:

- EDGAR ticker resolution succeeds for AMD;
- at least one AMD 10-K is downloaded or read from cache;
- parser extracts target sections;
- chunk count is greater than zero;
- embedding request succeeds through Gateway;
- SQLite receives chunk rows;
- Qdrant receives vector points.

Failure examples:

- SEC returns blocked/forbidden: check `SEC_USER_AGENT`.
- Gateway embedding call fails: check `http://localhost:8080/health`.
- Qdrant upsert fails: check Qdrant container and collection.
- SQLite write fails: confirm `fincontext.db` exists and schema was applied.

## 8. Validate The Ingestion Output

If PR #24 is merged, run the CLI:

```bash
python3 services/ingestion-worker/validate_ingestion.py \
  --db-path fincontext.db \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks \
  --citation-sample-size 20 \
  --ticker AMD
```

Expected messages:

```text
SQLite FTS is in sync: <N> chunks
Qdrant collection 'fincontext_chunks' is in sync: <N> points for <N> chunks
Citation anchors valid for 20 sampled chunks
Documents:
- AMD 10-K <filed_at>: <N> chunks; sections=...
```

If PR #24 is not merged, use this fallback:

```bash
PYTHONPATH=services/ingestion-worker python3 - <<'PY'
import sqlite3
from worker.validation import (
    inspect_citation_anchors,
    summarize_ingested_documents,
    validate_qdrant_count,
    validate_sqlite_fts,
)

conn = sqlite3.connect("fincontext.db")

checks = [
    validate_sqlite_fts(conn),
    validate_qdrant_count(conn, "http://localhost:6333"),
    inspect_citation_anchors(conn, sample_size=20),
]

for check in checks:
    print(check.message)
    if not check.ok:
        raise SystemExit(1)

for summary in summarize_ingested_documents(conn, ticker="AMD"):
    print(summary)
PY
```

Pass condition:

- SQLite chunk count equals searchable FTS rows;
- Qdrant point count equals SQLite chunk count;
- sampled citation anchors match paragraph/table format;
- document summary shows at least one AMD 10-K with nonzero chunks.

## 9. Manual SQLite Checks

Run:

```bash
sqlite3 fincontext.db "SELECT ticker, filing_type, filed_at, count(*) FROM chunks GROUP BY ticker, filing_type, filed_at;"
sqlite3 fincontext.db "SELECT citation_anchor FROM chunks WHERE ticker = 'AMD' LIMIT 20;"
sqlite3 fincontext.db "SELECT count(*) FROM chunks;"
```

Good sample citation anchors look like:

```text
AMD 10-K Item 1A paragraph 1
AMD 10-K Item 1A paragraph 2
AMD 10-K Item 8 table 1
```

Bad citation anchors include:

```text
paragraph one
AMD Item 1A 10-K paragraph 1
AMD 10-K Risk Factors paragraph 1
```

The exact required format is:

```text
{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}
{TICKER} {FILING_TYPE} {SECTION_LABEL} table {N}
```

## 10. Send Kishan This Handoff

After the smoke run, send Kishan:

```text
AMD one-filing ingestion smoke result:
- SQLite chunks count: <N>
- Qdrant points count: <N>
- Documents loaded:
  - AMD 10-K filed <date>, sections=<sections>, chunks=<N>
- Sample citation anchors:
  - <anchor 1>
  - <anchor 2>
  - <anchor 3>
- Source DB path on VM: <path>
- Qdrant collection: fincontext_chunks
- Retrieval contract doc: docs/ingestion-output-contract.md
```

Also tell him:

```text
Ingestion-side embeddings are done. The worker sends chunk text through Gateway
/v1/embeddings and writes 1024-dimensional vectors to Qdrant. The retrieval and
ranking part is separate: search SQLite BM25 and Qdrant, merge candidates with
RRF, then call Gateway /v1/rerank.
```

## 11. Snapshot After A Successful Smoke

Only snapshot after validation passes.

From repository root:

```bash
python3 infra/ops/demo_data_snapshots.py \
  --db-path fincontext.db \
  --backup-dir backups/demo-data \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks
```

Pass condition:

- timestamped SQLite backup is created under `backups/demo-data`;
- Qdrant snapshot name is printed;
- manifest JSON is written.

Do not commit anything under `backups/`.

## 12. Stop Conditions

Stop and coordinate if any of these happen:

- `rocm-smi` cannot see the GPU;
- model containers repeatedly restart;
- Gateway `/health` cannot see embeddings;
- ingestion writes SQLite chunks but Qdrant point count is zero;
- citation anchors do not match the required format;
- SQLite chunks exist but FTS validation fails;
- SEC blocks requests because of User-Agent;
- Qdrant collection has the wrong vector dimension.

Do not proceed to full demo ingestion until the one-filing AMD smoke test passes.

## 13. Next Step After This Passes

After this smoke test passes:

1. Run full demo ingestion for AMD, NVDA, MSFT, JPM, and TSLA.
2. Run validation again with a larger citation sample.
3. Snapshot SQLite and Qdrant.
4. Fill eval fixtures with real chunk IDs and citation anchors.
5. Hand sample retrieved chunks to Kishan for retrieval/reranker/UI citation-card work.
