# AMD One-Filing Ingestion Smoke Runbook

Live ingestion is not implemented in the current runnable stack. This runbook is
a target smoke test for the future ingestion worker.

## Current Readiness Check

Use the README-aligned stack first:

```bash
cp configs/.env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up --build
curl http://localhost:8090/api/health
curl http://localhost:8080/health
curl http://localhost:6333/healthz
```

## Future Preconditions

- `SEC_USER_AGENT` includes a real contact email.
- Gateway `/v1/embeddings` is configured and healthy.
- Qdrant collection `fincontext_chunks` exists with 1024-dimensional cosine
  vectors.
- SQLite has the agreed document/chunk schema.
- The ingestion worker exists and has offline tests.

## Future AMD Smoke

The first ingestion smoke should process one AMD 10-K and then validate:

- one document row was written;
- chunk rows were written;
- Qdrant point count matches chunk count;
- sampled citation anchors match the expected format;
- source URLs point to SEC EDGAR;
- rerunning the command does not create duplicates.

Do not run live ingestion during the judge demo.
