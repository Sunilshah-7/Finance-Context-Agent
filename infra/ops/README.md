# Infra Ops Utilities

This directory contains small operational scripts for preparing and preserving
demo data on the AMD VM. These scripts are not app services; they are commands
the team runs manually during setup, validation, and backup.

## AMD VM Preflight

Run the preflight before the longer ingestion smoke test:

```bash
python3 infra/ops/vm_preflight.py --env-path .env
```

The default mode is offline. It checks:

- the `.env` file exists;
- required `.env` values are not empty placeholders;
- SEC `User-Agent` includes a contact email;
- required repo files exist;
- required local commands exist;
- `rocm-smi` availability, as a warning on laptops.

On the AMD VM, make ROCm mandatory:

```bash
python3 infra/ops/vm_preflight.py --env-path .env --require-rocm
```

After Docker services and the Inference Gateway are running, use online mode:

```bash
python3 infra/ops/vm_preflight.py \
  --env-path .env \
  --require-rocm \
  --online
```

Online mode also checks:

- Qdrant health at `http://localhost:6333/healthz`;
- Inference Gateway health at `http://localhost:8080/health`.

Use JSON output when sharing a machine-readable status snapshot:

```bash
python3 infra/ops/vm_preflight.py --env-path .env --online --json
```

If the preflight fails, fix those errors before running EDGAR ingestion. The
goal is to catch missing secrets, missing scripts, missing commands, and dead
service endpoints before we spend GPU time loading models or debugging the
ingestion worker.

## Demo Data Snapshots

After a successful ingestion validation run, create a SQLite backup and Qdrant
snapshot:

```bash
python3 infra/ops/demo_data_snapshots.py \
  --db-path fincontext.db \
  --backup-dir backups/demo-data \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks
```

Generated backups and manifests stay under gitignored paths and should not be
committed.
