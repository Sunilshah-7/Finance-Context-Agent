# VM Ingestion Smoke Playbook

`README.md` is the source of truth. Live ingestion is not implemented in the
current runnable stack, so this playbook is a readiness checklist for future
ingestion work rather than a command-by-command guide for today.

## Current Stack Smoke

Start the current production-shaped stack:

```bash
cp configs/.env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up --build
```

Verify:

```bash
curl http://localhost:8090/api/health
curl http://localhost:8080/health
curl http://localhost:6333/healthz
```

The Agent API should report fixture mode and dependency status. Qdrant should be
healthy. Gateway health is degraded until `NIM_API_KEY` is configured.

## Future Ingestion Preconditions

Before running live ingestion, confirm:

- `SEC_USER_AGENT` includes a real contact email.
- Gateway `/v1/embeddings` is healthy.
- Qdrant `fincontext_chunks` exists with 1024-dimensional cosine vectors.
- SQLite has the agreed chunk/document schema.
- The ingestion command is idempotent and deduplicates by text hash.

## Future One-Filing Smoke

The first live ingestion smoke should process one AMD 10-K only, then validate:

- document row exists in SQLite;
- chunk rows exist in SQLite;
- Qdrant point count matches chunk count;
- citation anchors are stable and human-readable;
- source URLs point to SEC EDGAR;
- rerunning the same filing does not duplicate chunks.

## Demo Rule

Do not run live ingestion during the judge demo. Demo data should be prepared,
validated, snapshotted, and rehearsed beforehand.
