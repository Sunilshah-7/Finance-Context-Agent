from __future__ import annotations

import sqlite3

from worker.validation import inspect_citation_anchors


def test_inspect_citation_anchors_accepts_paragraph_and_table_formats():
    conn = _chunks_conn()
    conn.executemany(
        """
        INSERT INTO chunks (
            id, ticker, filing_type, filed_at, item_label,
            citation_anchor, is_table, chunk_index
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "chunk_1",
                "AMD",
                "10-K",
                "2025-02-14",
                "Item 1A",
                "AMD 10-K Item 1A paragraph 3",
                0,
                0,
            ),
            (
                "chunk_2",
                "AMD",
                "10-K",
                "2025-02-14",
                "Item 8",
                "AMD 10-K Item 8 table 2",
                1,
                1,
            ),
        ],
    )

    result = inspect_citation_anchors(conn, sample_size=20)

    assert result.ok is True
    assert result.sampled_count == 2
    assert result.invalid_anchors == []


def test_inspect_citation_anchors_reports_invalid_anchor():
    conn = _chunks_conn()
    conn.execute(
        """
        INSERT INTO chunks (
            id, ticker, filing_type, filed_at, item_label,
            citation_anchor, is_table, chunk_index
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "chunk_1",
            "AMD",
            "10-K",
            "2025-02-14",
            "Item 1A",
            "AMD 10-K Item 1A table 1",
            0,
            0,
        ),
    )

    result = inspect_citation_anchors(conn, sample_size=20)

    assert result.ok is False
    assert result.invalid_anchors[0].chunk_id == "chunk_1"
    assert result.invalid_anchors[0].expected_format == (
        "AMD 10-K Item 1A paragraph <N>"
    )
    assert "1 invalid of 1 sampled" in result.message


def _chunks_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE chunks (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            filing_type TEXT NOT NULL,
            filed_at TEXT NOT NULL,
            item_label TEXT NOT NULL,
            citation_anchor TEXT NOT NULL,
            is_table INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL
        )
        """
    )
    return conn
