from __future__ import annotations

import json
import re
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SqliteFtsValidation:
    chunks_count: int
    fts_count: int

    @property
    def ok(self) -> bool:
        return self.chunks_count == self.fts_count

    @property
    def message(self) -> str:
        if self.ok:
            return f"SQLite FTS is in sync: {self.chunks_count} chunks"
        return (
            "SQLite FTS mismatch: "
            f"chunks={self.chunks_count}, chunks_fts={self.fts_count}"
        )


def validate_sqlite_fts(conn: sqlite3.Connection) -> SqliteFtsValidation:
    chunks_count = _scalar_count(conn, "SELECT count(*) FROM chunks")
    fts_count = _count_searchable_fts_rows(conn)
    return SqliteFtsValidation(chunks_count=chunks_count, fts_count=fts_count)


def _scalar_count(conn: sqlite3.Connection, query: str) -> int:
    row = conn.execute(query).fetchone()
    if row is None:
        return 0
    return int(row[0])


def _count_searchable_fts_rows(conn: sqlite3.Connection) -> int:
    rows = conn.execute("SELECT rowid, text FROM chunks").fetchall()
    searchable = 0
    for rowid, text in rows:
        token = _first_search_token(str(text))
        if token is None:
            continue
        matched = conn.execute(
            "SELECT 1 FROM chunks_fts WHERE chunks_fts MATCH ? AND rowid = ? LIMIT 1",
            (token, rowid),
        ).fetchone()
        if matched is not None:
            searchable += 1
    return searchable


def _first_search_token(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9]{3,}", text)
    if match is None:
        return None
    return match.group(0)
