"""SQLite persistence helpers for ingestion output.

These functions upsert filing documents and chunk metadata into the schema in
``infra/schema.sql``. The chunk text lives in SQLite so later retrieval can use
the FTS5 BM25 index populated by database triggers.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from .models import ChunkInput, NormalizedDocument


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def upsert_document(conn: sqlite3.Connection, document: NormalizedDocument) -> str:
    sections_parsed = json.dumps([section.item_label for section in document.sections])
    conn.execute(
        """
        INSERT INTO documents (
            id, ticker, cik, company_name, filing_type, accession_number,
            filed_at, fiscal_period, source_url, local_path, sections_parsed, checksum
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            ticker = excluded.ticker,
            cik = excluded.cik,
            company_name = excluded.company_name,
            filing_type = excluded.filing_type,
            accession_number = excluded.accession_number,
            filed_at = excluded.filed_at,
            fiscal_period = excluded.fiscal_period,
            source_url = excluded.source_url,
            local_path = excluded.local_path,
            sections_parsed = excluded.sections_parsed,
            checksum = excluded.checksum
        """,
        (
            document.document_id,
            document.ticker,
            document.cik,
            document.company_name,
            document.filing_type,
            document.accession_number,
            document.filed_at,
            document.fiscal_period,
            document.source_url,
            document.local_path,
            sections_parsed,
            document.checksum,
        ),
    )
    return document.document_id


def upsert_chunks(conn: sqlite3.Connection, chunks: Iterable[ChunkInput]) -> int:
    chunk_list = list(chunks)
    if not chunk_list:
        return 0

    existing_hashes = get_existing_hashes(conn, [chunk.text_hash for chunk in chunk_list])
    new_chunks = [chunk for chunk in chunk_list if chunk.text_hash not in existing_hashes]
    if not new_chunks:
        return 0

    conn.executemany(
        """
        INSERT INTO chunks (
            id, document_id, ticker, filing_type, filed_at, section, item_label,
            section_title, chunk_index, text, text_hash, token_count,
            citation_anchor, source_url, is_table, vector_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        [
            (
                chunk.chunk_id,
                chunk.document_id,
                chunk.ticker,
                chunk.filing_type,
                chunk.filed_at,
                chunk.section,
                chunk.item_label,
                chunk.section_title,
                chunk.chunk_index,
                chunk.text,
                chunk.text_hash,
                chunk.token_count,
                chunk.citation_anchor,
                chunk.source_url,
                1 if chunk.is_table else 0,
                chunk.chunk_id,
            )
            for chunk in new_chunks
        ],
    )
    return len(new_chunks)


def get_existing_hashes(conn: sqlite3.Connection, text_hashes: list[str]) -> set[str]:
    if not text_hashes:
        return set()
    placeholders = ",".join("?" for _ in text_hashes)
    rows = conn.execute(
        f"SELECT text_hash FROM chunks WHERE text_hash IN ({placeholders})",
        text_hashes,
    ).fetchall()
    return {str(row["text_hash"]) for row in rows}


def count_chunks(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT count(*) AS count FROM chunks").fetchone()
    return int(row["count"])


def count_fts_chunks(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT count(*) AS count FROM chunks_fts").fetchone()
    return int(row["count"])
