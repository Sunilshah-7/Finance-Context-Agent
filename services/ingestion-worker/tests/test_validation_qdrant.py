from __future__ import annotations

import sqlite3

import pytest

from worker import validation


def test_parse_qdrant_count_response_reads_result_count():
    payload = {"result": {"count": 42}, "status": "ok", "time": 0.001}

    assert validation.parse_qdrant_count_response(payload) == 42
    assert validation.parse_qdrant_count_response(b'{"result":{"count":42}}') == 42


def test_parse_qdrant_count_response_rejects_missing_count():
    with pytest.raises(ValueError, match="result.count"):
        validation.parse_qdrant_count_response({"result": {}})


def test_validate_qdrant_count_compares_points_to_sqlite_chunks(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE chunks (id TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO chunks (id) VALUES (?)", [("chunk_1",), ("chunk_2",)])

    monkeypatch.setattr(validation, "fetch_qdrant_point_count", lambda **_: 1)

    result = validation.validate_qdrant_count(
        conn,
        qdrant_url="http://qdrant.local",
        collection="fincontext_chunks",
    )

    assert result.ok is False
    assert result.sqlite_chunks_count == 2
    assert result.qdrant_points_count == 1
    assert "sqlite_chunks=2, qdrant_points=1" in result.message
