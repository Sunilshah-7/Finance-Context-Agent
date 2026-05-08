from __future__ import annotations

import sqlite3
from pathlib import Path

from worker.db import upsert_chunks, upsert_document
from worker.models import ChunkInput, NormalizedDocument, NormalizedSection
from worker.validation import validate_sqlite_fts


def test_validate_sqlite_fts_reports_synced_counts(tmp_path):
    conn = _schema_conn(tmp_path)
    upsert_document(conn, _document())
    upsert_chunks(conn, [_chunk("chunk_1", "hash_1")])
    conn.commit()

    result = validate_sqlite_fts(conn)

    assert result.ok is True
    assert result.chunks_count == 1
    assert result.fts_count == 1
    assert result.message == "SQLite FTS is in sync: 1 chunks"


def test_validate_sqlite_fts_reports_mismatch(tmp_path):
    conn = _schema_conn(tmp_path)
    upsert_document(conn, _document())
    upsert_chunks(conn, [_chunk("chunk_1", "hash_1")])
    conn.execute("DELETE FROM chunks_fts")
    conn.commit()

    result = validate_sqlite_fts(conn)

    assert result.ok is False
    assert "chunks=1, chunks_fts=0" in result.message


def _schema_conn(tmp_path) -> sqlite3.Connection:
    schema_path = Path(__file__).resolve().parents[3] / "infra" / "schema.sql"
    conn = sqlite3.connect(tmp_path / "fincontext.db")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    return conn


def _document() -> NormalizedDocument:
    return NormalizedDocument(
        document_id="doc_1",
        ticker="AMD",
        cik="0000002488",
        filing_type="10-K",
        accession_number="0000002488-25-000012",
        filed_at="2025-02-14",
        fiscal_period="FY2024",
        source_url="https://www.sec.gov/example",
        sections=[
            NormalizedSection(
                section_id="item_1a",
                item_label="Item 1A",
                title="Risk Factors",
                text="Supply chain risk text.",
                word_count=4,
            )
        ],
    )


def _chunk(chunk_id: str, text_hash: str) -> ChunkInput:
    return ChunkInput(
        chunk_id=chunk_id,
        document_id="doc_1",
        ticker="AMD",
        cik="0000002488",
        filing_type="10-K",
        accession_number="0000002488-25-000012",
        filed_at="2025-02-14",
        fiscal_period="FY2024",
        section="item_1a",
        item_label="Item 1A",
        section_title="Risk Factors",
        chunk_index=0,
        text="Supply chain risk text.",
        text_hash=text_hash,
        token_count=5,
        citation_anchor="AMD 10-K Item 1A paragraph 1",
        source_url="https://www.sec.gov/example",
    )
