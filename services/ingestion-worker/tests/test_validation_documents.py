from __future__ import annotations

import sqlite3

from worker.validation import summarize_ingested_documents


def test_summarize_ingested_documents_lists_sections_and_chunk_counts():
    conn = _summary_conn()
    conn.executemany(
        """
        INSERT INTO documents (
            id, ticker, filing_type, filed_at, sections_parsed
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("doc_amd_2025", "AMD", "10-K", "2025-02-14", '["Item 1", "Item 1A"]'),
            ("doc_nvda_2025", "NVDA", "10-Q", "2025-05-28", '["Item 1A"]'),
        ],
    )
    conn.executemany(
        "INSERT INTO chunks (id, document_id) VALUES (?, ?)",
        [
            ("chunk_1", "doc_amd_2025"),
            ("chunk_2", "doc_amd_2025"),
            ("chunk_3", "doc_nvda_2025"),
        ],
    )

    summaries = summarize_ingested_documents(conn, ticker="amd")

    assert len(summaries) == 1
    assert summaries[0].document_id == "doc_amd_2025"
    assert summaries[0].ticker == "AMD"
    assert summaries[0].filing_type == "10-K"
    assert summaries[0].filed_at == "2025-02-14"
    assert summaries[0].sections_parsed == ["Item 1", "Item 1A"]
    assert summaries[0].chunk_count == 2


def _summary_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            filing_type TEXT NOT NULL,
            filed_at TEXT NOT NULL,
            sections_parsed TEXT
        );
        CREATE TABLE chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL
        );
        """
    )
    return conn
