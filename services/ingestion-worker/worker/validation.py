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


@dataclass(frozen=True)
class QdrantCountValidation:
    sqlite_chunks_count: int
    qdrant_points_count: int
    collection: str
    allowed_delta: int = 0

    @property
    def delta(self) -> int:
        return abs(self.sqlite_chunks_count - self.qdrant_points_count)

    @property
    def ok(self) -> bool:
        return self.delta <= self.allowed_delta

    @property
    def message(self) -> str:
        if self.ok:
            return (
                f"Qdrant collection {self.collection!r} is in sync: "
                f"{self.qdrant_points_count} points for {self.sqlite_chunks_count} chunks"
            )
        return (
            f"Qdrant count mismatch for {self.collection!r}: "
            f"sqlite_chunks={self.sqlite_chunks_count}, "
            f"qdrant_points={self.qdrant_points_count}, "
            f"allowed_delta={self.allowed_delta}"
        )


def validate_sqlite_fts(conn: sqlite3.Connection) -> SqliteFtsValidation:
    chunks_count = _scalar_count(conn, "SELECT count(*) FROM chunks")
    fts_count = _count_searchable_fts_rows(conn)
    return SqliteFtsValidation(chunks_count=chunks_count, fts_count=fts_count)


def validate_qdrant_count(
    conn: sqlite3.Connection,
    qdrant_url: str,
    collection: str = "fincontext_chunks",
    allowed_delta: int = 0,
    timeout_seconds: float = 10.0,
) -> QdrantCountValidation:
    sqlite_chunks_count = _scalar_count(conn, "SELECT count(*) FROM chunks")
    qdrant_points_count = fetch_qdrant_point_count(
        qdrant_url=qdrant_url,
        collection=collection,
        timeout_seconds=timeout_seconds,
    )
    return QdrantCountValidation(
        sqlite_chunks_count=sqlite_chunks_count,
        qdrant_points_count=qdrant_points_count,
        collection=collection,
        allowed_delta=allowed_delta,
    )


def fetch_qdrant_point_count(
    qdrant_url: str,
    collection: str = "fincontext_chunks",
    timeout_seconds: float = 10.0,
) -> int:
    base_url = qdrant_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/points/count"
    data = json.dumps({"exact": True}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Qdrant count request failed with {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Qdrant count request failed: {exc.reason}") from exc
    return parse_qdrant_count_response(payload)


def parse_qdrant_count_response(payload: str | bytes | dict[str, Any]) -> int:
    if isinstance(payload, bytes):
        parsed: dict[str, Any] = json.loads(payload.decode("utf-8"))
    elif isinstance(payload, str):
        parsed = json.loads(payload)
    else:
        parsed = payload

    result = parsed.get("result")
    if not isinstance(result, dict) or "count" not in result:
        raise ValueError("Qdrant count response is missing result.count")
    return int(result["count"])


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
