"""Export citation-ready ingestion samples for retrieval and UI handoff.

This module reads the SQLite `documents` and `chunks` tables after ingestion
and produces a compact JSON payload for teammates. Kishan can use the output to
see the exact chunk IDs, citation anchors, source URLs, and text snippets that
retrieval, reranking, memo generation, and citation cards will consume.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LIMIT = 50
DEFAULT_PREVIEW_CHARS = 500


@dataclass(frozen=True)
class HandoffFilters:
    tickers: list[str] | None = None
    filing_types: list[str] | None = None
    sections: list[str] | None = None
    limit: int = DEFAULT_LIMIT
    include_full_text: bool = False
    preview_chars: int = DEFAULT_PREVIEW_CHARS


def build_handoff_export(
    conn: sqlite3.Connection,
    *,
    filters: HandoffFilters | None = None,
) -> dict[str, Any]:
    """Build a deterministic JSON-serializable export from ingested chunks."""

    filters = filters or HandoffFilters()
    conn.row_factory = sqlite3.Row
    chunk_rows = fetch_chunk_rows(conn, filters)
    document_ids = sorted({str(row["document_id"]) for row in chunk_rows})
    document_rows = fetch_document_rows(conn, document_ids)

    return {
        "description": (
            "Citation-ready ingestion handoff for retrieval, reranking, memo, "
            "and UI citation-card work."
        ),
        "filters": {
            "tickers": filters.tickers or [],
            "filing_types": filters.filing_types or [],
            "sections": filters.sections or [],
            "limit": filters.limit,
            "include_full_text": filters.include_full_text,
            "preview_chars": filters.preview_chars,
        },
        "counts": {
            "documents": len(document_rows),
            "chunks": len(chunk_rows),
        },
        "documents": [format_document(row) for row in document_rows],
        "chunks": [format_chunk(row, filters) for row in chunk_rows],
    }


def fetch_chunk_rows(
    conn: sqlite3.Connection,
    filters: HandoffFilters,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list[Any] = []

    if filters.tickers:
        clauses.append(f"c.ticker IN ({placeholders(filters.tickers)})")
        params.extend(ticker.upper() for ticker in filters.tickers)
    if filters.filing_types:
        clauses.append(f"c.filing_type IN ({placeholders(filters.filing_types)})")
        params.extend(filters.filing_types)
    if filters.sections:
        clauses.append(
            "("
            f"c.item_label IN ({placeholders(filters.sections)}) "
            "OR "
            f"c.section IN ({placeholders(filters.sections)})"
            ")"
        )
        params.extend(filters.sections)
        params.extend(filters.sections)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(filters.limit)

    return conn.execute(
        f"""
        SELECT
            c.id,
            c.document_id,
            c.ticker,
            c.filing_type,
            c.filed_at,
            c.section,
            c.item_label,
            c.section_title,
            c.chunk_index,
            c.text,
            c.text_hash,
            c.token_count,
            c.citation_anchor,
            c.source_url,
            c.is_table,
            c.vector_id,
            d.cik,
            d.company_name,
            d.accession_number,
            d.fiscal_period
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        {where_clause}
        ORDER BY c.ticker, c.filed_at DESC, c.filing_type, c.section, c.chunk_index, c.id
        LIMIT ?
        """,
        params,
    ).fetchall()


def fetch_document_rows(
    conn: sqlite3.Connection,
    document_ids: list[str],
) -> list[sqlite3.Row]:
    if not document_ids:
        return []
    return conn.execute(
        f"""
        SELECT
            d.id,
            d.ticker,
            d.cik,
            d.company_name,
            d.filing_type,
            d.accession_number,
            d.filed_at,
            d.fiscal_period,
            d.source_url,
            d.sections_parsed,
            count(c.id) AS chunk_count
        FROM documents d
        LEFT JOIN chunks c ON c.document_id = d.id
        WHERE d.id IN ({placeholders(document_ids)})
        GROUP BY
            d.id,
            d.ticker,
            d.cik,
            d.company_name,
            d.filing_type,
            d.accession_number,
            d.filed_at,
            d.fiscal_period,
            d.source_url,
            d.sections_parsed
        ORDER BY d.ticker, d.filed_at DESC, d.filing_type, d.id
        """,
        document_ids,
    ).fetchall()


def format_document(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "document_id": row["id"],
        "ticker": row["ticker"],
        "cik": row["cik"],
        "company_name": row["company_name"],
        "filing_type": row["filing_type"],
        "accession_number": row["accession_number"],
        "filed_at": row["filed_at"],
        "fiscal_period": row["fiscal_period"],
        "source_url": row["source_url"],
        "sections_parsed": parse_sections(row["sections_parsed"]),
        "chunk_count": int(row["chunk_count"]),
    }


def format_chunk(row: sqlite3.Row, filters: HandoffFilters) -> dict[str, Any]:
    text = str(row["text"])
    chunk = {
        "chunk_id": row["id"],
        "qdrant_point_id": row["vector_id"] or row["id"],
        "document_id": row["document_id"],
        "ticker": row["ticker"],
        "cik": row["cik"],
        "company_name": row["company_name"],
        "filing_type": row["filing_type"],
        "accession_number": row["accession_number"],
        "filed_at": row["filed_at"],
        "fiscal_period": row["fiscal_period"],
        "section": row["section"],
        "item_label": row["item_label"],
        "section_title": row["section_title"],
        "chunk_index": int(row["chunk_index"]),
        "token_count": int(row["token_count"] or 0),
        "text_hash": row["text_hash"],
        "citation_anchor": row["citation_anchor"],
        "source_url": row["source_url"],
        "is_table": bool(row["is_table"]),
        "text_preview": preview_text(text, filters.preview_chars),
    }
    if filters.include_full_text:
        chunk["text"] = text
    return chunk


def parse_sections(raw_sections: str | None) -> list[str]:
    if not raw_sections:
        return []
    try:
        parsed = json.loads(raw_sections)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(section) for section in parsed]


def preview_text(text: str, preview_chars: int) -> str:
    compact = " ".join(text.split())
    if preview_chars <= 0 or len(compact) <= preview_chars:
        return compact
    return compact[:preview_chars].rstrip() + "..."


def placeholders(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def parse_csv_filter(raw_value: str | None) -> list[str] | None:
    if not raw_value:
        return None
    values = [value.strip() for value in raw_value.split(",") if value.strip()]
    return values or None


def write_handoff_export(payload: dict[str, Any], output_path: str | None) -> None:
    rendered = json.dumps(payload, indent=2) + "\n"
    if not output_path or output_path == "-":
        print(rendered, end="")
        return
    Path(output_path).write_text(rendered, encoding="utf-8")
