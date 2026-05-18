# AMD One-Filing Ingestion Smoke Runbook

Use this runbook after PR #17 is merged and the Inference Gateway, Qdrant, and SQLite are available on the backend host or a local equivalent. This is a pre-demo validation path only. Do not run live ingestion during the judge demo.

## Prerequisites

- `SEC_USER_AGENT` is set to a real contact email, for example `FinContextAgent/0.1 name@example.com`.
- Inference Gateway is running on `http://localhost:8080` and exposes `POST /v1/embeddings`.
- Qdrant is running on `http://localhost:6333`.
- Run commands from the repository root unless noted.

## Initialize Storage

```bash
sqlite3 fincontext.db < infra/schema.sql
python3 infra/qdrant/init_collection.py --qdrant-url http://localhost:6333 --collection fincontext_chunks
```

Use `--recreate` on the Qdrant init script only when intentionally discarding previously loaded points.

## Run One-Filing AMD Ingestion

```bash
cd services/ingestion-worker
python3 ingest.py \
  --tickers AMD \
  --filing-types 10-K \
  --years 1 \
  --db-path ../../fincontext.db \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks \
  --gateway-url http://localhost:8080
```

Expected result: the command finishes without EDGAR, Gateway, SQLite, or Qdrant errors and writes AMD 10-K chunks with citation anchors such as `AMD 10-K Item 1A paragraph 1`.

## Run Validation Helpers

```bash
python3 services/ingestion-worker/validate_ingestion.py \
  --db-path fincontext.db \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks \
  --citation-sample-size 20 \
  --ticker AMD
```

## Pass Conditions

- SQLite FTS is in sync: `chunks` and searchable `chunks_fts` rows match.
- Qdrant point count matches SQLite chunk count, or any mismatch is explained before full demo ingestion.
- At least 20 sampled citation anchors match the exact paragraph/table format.
- Document summary lists AMD `10-K`, filed date, parsed sections, and nonzero chunk count.

## Deferred Until Runtime Services Are Ready

- Real EDGAR network run.
- Real Gateway embedding request.
- Real Qdrant point-count verification.
- Manual inspection of 20 source URLs and citation anchors.
