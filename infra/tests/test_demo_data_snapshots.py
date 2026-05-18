"""Tests for demo data backup/snapshot ops helpers.

The tests cover SQLite backup behavior and Qdrant request/response handling
without requiring a live Qdrant server.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "ops" / "demo_data_snapshots.py"
)
SPEC = importlib.util.spec_from_file_location("demo_data_snapshots", MODULE_PATH)
assert SPEC is not None
demo_data_snapshots = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(demo_data_snapshots)


def test_backup_sqlite_database_copies_source_database(tmp_path):
    source_path = tmp_path / "fincontext.db"
    backup_path = tmp_path / "backups" / "fincontext_demo.db"
    source = sqlite3.connect(source_path)
    source.execute("CREATE TABLE chunks (id TEXT PRIMARY KEY, text TEXT NOT NULL)")
    source.execute("INSERT INTO chunks (id, text) VALUES ('chunk_1', 'risk text')")
    source.commit()
    source.close()

    result = demo_data_snapshots.backup_sqlite_database(source_path, backup_path)

    backup = sqlite3.connect(result)
    row = backup.execute("SELECT id, text FROM chunks").fetchone()
    backup.close()
    assert row == ("chunk_1", "risk text")


def test_default_sqlite_backup_path_uses_timestamped_demo_name(tmp_path):
    path = demo_data_snapshots.default_sqlite_backup_path(tmp_path, "20260508-010203")

    assert path == tmp_path / "fincontext_demo_20260508-010203.db"


def test_parse_qdrant_snapshot_name_reads_result_name():
    payload = {"result": {"name": "fincontext_chunks-123.snapshot"}}

    assert (
        demo_data_snapshots.parse_qdrant_snapshot_name(payload)
        == "fincontext_chunks-123.snapshot"
    )


def test_create_qdrant_snapshot_posts_to_collection_snapshots(monkeypatch):
    calls = []

    def fake_request_json(method, url, body=None, timeout=10.0):
        calls.append((method, url, body, timeout))
        return {"result": {"name": "snapshot-1"}}

    monkeypatch.setattr(demo_data_snapshots, "request_json", fake_request_json)

    name = demo_data_snapshots.create_qdrant_snapshot(
        "http://qdrant.local/",
        collection="fincontext_chunks",
        timeout=12.0,
    )

    assert name == "snapshot-1"
    assert calls == [
        (
            "POST",
            "http://qdrant.local/collections/fincontext_chunks/snapshots",
            None,
            12.0,
        )
    ]


def test_write_manifest_records_backup_and_snapshot(tmp_path):
    manifest_path = tmp_path / "manifest.json"

    result = demo_data_snapshots.write_manifest(
        manifest_path,
        timestamp="20260508-010203",
        sqlite_backup_path=tmp_path / "fincontext_demo.db",
        qdrant_snapshot_name="snapshot-1",
        qdrant_collection="fincontext_chunks",
    )

    manifest = json.loads(result.read_text(encoding="utf-8"))
    assert manifest == {
        "created_at_utc": "20260508-010203",
        "sqlite_backup_path": str(tmp_path / "fincontext_demo.db"),
        "qdrant_collection": "fincontext_chunks",
        "qdrant_snapshot_name": "snapshot-1",
    }
