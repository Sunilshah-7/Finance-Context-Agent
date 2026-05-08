from __future__ import annotations

import importlib.util
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
