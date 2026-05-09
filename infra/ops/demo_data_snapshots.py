#!/usr/bin/env python3
"""Create repeatable demo-data backups after ingestion succeeds.

This CLI copies the SQLite metadata DB, asks Qdrant to snapshot the
``fincontext_chunks`` collection, and writes a manifest tying both artifacts
together. Generated backups stay under gitignored paths and should not be
committed.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = "fincontext.db"
DEFAULT_BACKUP_DIR = "backups/demo-data"
DEFAULT_COLLECTION = "fincontext_chunks"
DEFAULT_QDRANT_URL = "http://localhost:6333"


def backup_sqlite_database(source_path: Path, backup_path: Path) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    return backup_path


def default_sqlite_backup_path(backup_dir: Path, timestamp: str) -> Path:
    return backup_dir / f"fincontext_demo_{timestamp}.db"


def create_qdrant_snapshot(
    qdrant_url: str,
    collection: str = DEFAULT_COLLECTION,
    timeout: float = 30.0,
) -> str:
    base_url = qdrant_url.rstrip("/")
    payload = request_json(
        "POST",
        f"{base_url}/collections/{collection}/snapshots",
        timeout=timeout,
    )
    return parse_qdrant_snapshot_name(payload)


def parse_qdrant_snapshot_name(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("Qdrant snapshot response is missing result")
    name = result.get("name")
    if not name:
        raise ValueError("Qdrant snapshot response is missing result.name")
    return str(name)


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def write_manifest(
    manifest_path: Path,
    *,
    timestamp: str,
    sqlite_backup_path: Path | None,
    qdrant_snapshot_name: str | None,
    qdrant_collection: str,
) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at_utc": timestamp,
        "sqlite_backup_path": str(sqlite_backup_path) if sqlite_backup_path else None,
        "qdrant_collection": qdrant_collection,
        "qdrant_snapshot_name": qdrant_snapshot_name,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def default_manifest_path(backup_dir: Path, timestamp: str) -> Path:
    return backup_dir / f"demo_data_manifest_{timestamp}.json"


def timestamp_slug() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create demo-data backups for SQLite and Qdrant."
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("SQLITE_DB_PATH", DEFAULT_DB_PATH),
        help=f"SQLite DB path. Defaults to SQLITE_DB_PATH or {DEFAULT_DB_PATH}.",
    )
    parser.add_argument(
        "--backup-dir",
        default=DEFAULT_BACKUP_DIR,
        help=f"Backup output directory. Defaults to {DEFAULT_BACKUP_DIR}.",
    )
    parser.add_argument(
        "--sqlite-output",
        help="Optional explicit SQLite backup path.",
    )
    parser.add_argument(
        "--skip-sqlite",
        action="store_true",
        help="Skip SQLite backup creation.",
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL),
        help=f"Qdrant REST URL. Defaults to QDRANT_URL or {DEFAULT_QDRANT_URL}.",
    )
    parser.add_argument(
        "--qdrant-collection",
        default=os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION),
        help=f"Qdrant collection name. Defaults to QDRANT_COLLECTION or {DEFAULT_COLLECTION}.",
    )
    parser.add_argument(
        "--skip-qdrant",
        action="store_true",
        help="Skip Qdrant snapshot creation.",
    )
    parser.add_argument(
        "--manifest-output",
        help="Optional explicit JSON manifest path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = timestamp_slug()
    backup_dir = Path(args.backup_dir)
    sqlite_backup_path: Path | None = None
    qdrant_snapshot_name: str | None = None

    try:
        if not args.skip_sqlite:
            sqlite_backup_path = (
                Path(args.sqlite_output)
                if args.sqlite_output
                else default_sqlite_backup_path(backup_dir, timestamp)
            )
            backup_sqlite_database(Path(args.db_path), sqlite_backup_path)
            print(f"SQLite backup created: {sqlite_backup_path}")
        if not args.skip_qdrant:
            qdrant_snapshot_name = create_qdrant_snapshot(
                args.qdrant_url,
                collection=args.qdrant_collection,
            )
            print(
                "Qdrant snapshot created: "
                f"{args.qdrant_collection}/{qdrant_snapshot_name}"
            )
        manifest_path = (
            Path(args.manifest_output)
            if args.manifest_output
            else default_manifest_path(backup_dir, timestamp)
        )
        write_manifest(
            manifest_path,
            timestamp=timestamp,
            sqlite_backup_path=sqlite_backup_path,
            qdrant_snapshot_name=qdrant_snapshot_name,
            qdrant_collection=args.qdrant_collection,
        )
        print(f"Manifest written: {manifest_path}")
    except Exception as exc:  # noqa: BLE001 - CLI should print actionable failures
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
