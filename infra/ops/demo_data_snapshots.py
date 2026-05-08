#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = timestamp_slug()
    backup_dir = Path(args.backup_dir)

    try:
        if not args.skip_sqlite:
            sqlite_backup_path = (
                Path(args.sqlite_output)
                if args.sqlite_output
                else default_sqlite_backup_path(backup_dir, timestamp)
            )
            backup_sqlite_database(Path(args.db_path), sqlite_backup_path)
            print(f"SQLite backup created: {sqlite_backup_path}")
    except Exception as exc:  # noqa: BLE001 - CLI should print actionable failures
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
