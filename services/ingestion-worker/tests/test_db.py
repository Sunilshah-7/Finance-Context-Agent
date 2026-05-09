"""SQLite/Qdrant payload tests for ingestion persistence contracts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from worker.db import count_chunks, count_fts_chunks, upsert_chunks, upsert_document
from worker.models import ChunkInput, NormalizedDocument, NormalizedSection
from worker.vector_store import build_payload


def test_sqlite_writer_inserts_chunks_and_fts_rows(tmp_path):
    db_path = tmp_path / "fincontext.db"
    schema_path = Path(__file__).resolve().parents[3] / "infra" / "schema.sql"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(schema_path.read_text(encoding="utf-8"))

    document = NormalizedDocument(
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
    chunk = ChunkInput(
        chunk_id="chunk_1",
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
        text_hash="abc123def4567890",
        token_count=5,
        citation_anchor="AMD 10-K Item 1A paragraph 1",
        source_url="https://www.sec.gov/example",
    )

    upsert_document(conn, document)
    assert upsert_chunks(conn, [chunk]) == 1
    assert upsert_chunks(conn, [chunk]) == 0
    conn.commit()

    assert count_chunks(conn) == 1
    assert count_fts_chunks(conn) == 1


def test_build_qdrant_payload_from_chunk():
    chunk = ChunkInput(
        chunk_id="chunk_1",
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
        text_hash="abc123def4567890",
        token_count=5,
        citation_anchor="AMD 10-K Item 1A paragraph 1",
        source_url="https://www.sec.gov/example",
    )

    payload = build_payload(chunk.model_copy(update={"embedding": [0.1] * 1024}))
    assert payload.chunk_id == "chunk_1"
    assert payload.ticker == "AMD"
    assert payload.citation_anchor == "AMD 10-K Item 1A paragraph 1"
