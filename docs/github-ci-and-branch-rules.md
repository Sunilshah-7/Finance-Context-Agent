# GitHub CI And Branch Rules

`README.md` is the source of truth. CI should protect the current Go-first
runtime without requiring live NVIDIA NIM, EDGAR, Qdrant integration, or
HuggingFace deployment.

## Recommended CI Checks

### Go Backend Tests

```bash
cd backend
GOCACHE=$PWD/../.gocache GOMODCACHE=$PWD/../.gomodcache go test ./...
```

Use absolute cache paths in CI if the Go toolchain requires them.

### Frontend Build

```bash
cd apps/demo-ui
npm ci
npm run build
```

### Repository Policy

Block accidental commits of:

- `.env` files;
- SQLite database files;
- Qdrant storage;
- model caches;
- generated backups;
- `__pycache__`, `.pyc`, `.pytest_cache`;
- local build/test output directories.

## What CI Should Not Require

- Live NVIDIA NIM calls.
- Live EDGAR ingestion.
- Live Qdrant data integration.
- HuggingFace Spaces deployment.
- Secrets in pull-request contexts.

## Recommended Branch Rules

For `dev` and `main`:

- Require a pull request before merging.
- Require at least one approval.
- Require status checks to pass.
- Do not allow force pushes.
- Do not allow deletions.

All feature work should branch from `dev` and PR back to `dev`. Promotions from
`dev` to `main` should happen only at stable milestones.
