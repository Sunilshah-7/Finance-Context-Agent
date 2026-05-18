# Demo Data Backup and Snapshot Ops

Use this after a successful full demo ingestion run. The goal is to preserve the exact SQLite metadata and Qdrant vector collection used for rehearsal and demo day.

Run from the repository root on the AMD VM:

```bash
python3 infra/ops/demo_data_snapshots.py \
  --db-path fincontext.db \
  --backup-dir backups/demo-data \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks
```

The command creates:

- a timestamped SQLite backup, for example `backups/demo-data/fincontext_demo_20260508-010203.db`
- a Qdrant collection snapshot inside Qdrant storage for `fincontext_chunks`
- a JSON manifest linking the SQLite backup path and Qdrant snapshot name

For SQLite-only backup, useful before Qdrant is online:

```bash
python3 infra/ops/demo_data_snapshots.py \
  --db-path fincontext.db \
  --backup-dir backups/demo-data \
  --skip-qdrant
```

For Qdrant-only snapshot, useful after refreshing vector points without changing SQLite:

```bash
python3 infra/ops/demo_data_snapshots.py \
  --skip-sqlite \
  --qdrant-url http://localhost:6333 \
  --qdrant-collection fincontext_chunks
```

Generated backups and manifests live under `backups/`, which is gitignored. Do not commit SQLite DB files, Qdrant storage, model caches, or copied snapshots.

## Restore Notes

SQLite restore is a file copy:

```bash
cp backups/demo-data/fincontext_demo_YYYYMMDD-HHMMSS.db fincontext.db
```

Qdrant snapshot restore should be done deliberately on the VM after confirming whether the target collection should be replaced. Keep the manifest next to the copied snapshot so the matching SQLite DB and Qdrant collection version are traceable.
