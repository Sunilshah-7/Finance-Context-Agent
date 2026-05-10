from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, Range

try:
    from fincontext_schemas import EvidenceChunk, RetrievalPlan
except ModuleNotFoundError:  # local Python may not have the editable package installed
    schema_src = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "python"
    sys.path.insert(0, str(schema_src))
    from state import EvidenceChunk, RetrievalPlan  # type: ignore[no-redef]


logger = logging.getLogger(__name__)

DEFAULT_QDRANT_COLLECTION = "fincontext_chunks"
DEFAULT_SQLITE_PATH = "./fincontext.db"
DEFAULT_GATEWAY_URL = "http://localhost:8080"
EMBEDDING_MODEL_NAME = "fincontext-embedding"


def _resolve_sqlite_path(sqlite_path: str | None) -> str:
    return sqlite_path or os.getenv("SQLITE_DB_PATH", DEFAULT_SQLITE_PATH)


def _resolve_qdrant_url(qdrant_url: str | None) -> str:
    return qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")


def _resolve_gateway_url(gateway_url: str | None) -> str:
    return gateway_url or os.getenv("INFERENCE_GATEWAY_URL", DEFAULT_GATEWAY_URL)


def _resolve_qdrant_collection() -> str:
    return os.getenv("QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION)


def _escape_fts5_phrase(value: str) -> str:
    token = value.replace('"', '""').strip()
    return f'"{token}"'


def _build_match_expression(keywords: list[str]) -> str:
    cleaned = [keyword.strip() for keyword in keywords if keyword and keyword.strip()]
    if not cleaned:
        return '""'
    return " OR ".join(_escape_fts5_phrase(keyword) for keyword in cleaned)


def _row_to_evidence_chunk(row: sqlite3.Row, *, score: float) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=str(row["chunk_id"]),
        document_id=str(row["document_id"]),
        ticker=str(row["ticker"]),
        filing_type=str(row["filing_type"]),
        filed_at=str(row["filed_at"]),
        section=str(row["section"]),
        item_label=str(row["item_label"] or ""),
        text=str(row["text"]),
        citation_anchor=str(row["citation_anchor"]),
        source_url=str(row["source_url"] or ""),
        chunk_index=int(row["chunk_index"]),
        rerank_score=score,
    )


def _payload_to_evidence_chunk(payload: dict[str, Any], *, score: float) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=str(payload["chunk_id"]),
        document_id=str(payload["document_id"]),
        ticker=str(payload["ticker"]),
        filing_type=str(payload["filing_type"]),
        filed_at=str(payload["filed_at"]),
        section=str(payload["section"]),
        item_label=str(payload.get("item_label") or ""),
        text=str(payload.get("text") or ""),
        citation_anchor=str(payload["citation_anchor"]),
        source_url=str(payload.get("source_url") or ""),
        chunk_index=int(payload["chunk_index"]),
        rerank_score=score,
    )


def _in_clause(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def _build_bm25_sql(
    *,
    tickers: list[str] | None,
    sections: list[str] | None,
    filing_types: list[str] | None,
    date_range_start: str | None,
    date_range_end: str | None,
) -> tuple[str, list[Any]]:
    sql = """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.ticker,
            c.filing_type,
            c.filed_at,
            c.section,
            c.item_label,
            c.text,
            c.citation_anchor,
            c.source_url,
            c.chunk_index,
            bm25(chunks_fts) AS bm25_score
        FROM chunks_fts
        JOIN chunks c ON c.rowid = chunks_fts.rowid
        WHERE chunks_fts MATCH ?
    """
    params: list[Any] = []

    if tickers:
        sql += f" AND c.ticker IN ({_in_clause(tickers)})"
        params.extend(tickers)

    if sections:
        sql += f" AND c.section IN ({_in_clause(sections)})"
        params.extend(sections)

    if filing_types:
        sql += f" AND c.filing_type IN ({_in_clause(filing_types)})"
        params.extend(filing_types)

    if date_range_start is not None:
        sql += " AND c.filed_at >= ?"
        params.append(date_range_start)

    if date_range_end is not None:
        sql += " AND c.filed_at <= ?"
        params.append(date_range_end)

    sql += " ORDER BY bm25_score ASC LIMIT ?"
    return sql, params


def _run_bm25_query(
    *,
    keywords: list[str],
    tickers: list[str] | None,
    sections: list[str] | None,
    filing_types: list[str] | None,
    date_range_start: str | None,
    date_range_end: str | None,
    k: int,
    sqlite_path: str,
) -> list[EvidenceChunk]:
    match_expression = _build_match_expression(keywords)
    sql, extra_params = _build_bm25_sql(
        tickers=tickers,
        sections=sections,
        filing_types=filing_types,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, [match_expression, *extra_params, k]).fetchall()
    finally:
        conn.close()

    return [
        _row_to_evidence_chunk(row, score=-float(row["bm25_score"]))
        for row in rows
    ]


async def bm25_search(
    keywords: list[str],
    tickers: list[str] | None = None,
    sections: list[str] | None = None,
    filing_types: list[str] | None = None,
    date_range_start: str | None = None,
    date_range_end: str | None = None,
    k: int = 30,
    sqlite_path: str | None = None,
) -> list[EvidenceChunk]:
    """Run SQLite FTS5 BM25 retrieval using keyword phrases and relational metadata filters."""
    resolved_sqlite_path = _resolve_sqlite_path(sqlite_path)
    return await asyncio.to_thread(
        _run_bm25_query,
        keywords=keywords,
        tickers=tickers,
        sections=sections,
        filing_types=filing_types,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        k=k,
        sqlite_path=resolved_sqlite_path,
    )


async def _embed_query(query: str, gateway_url: str) -> list[float]:
    # TODO: replace with gateway client when services/agent-api/app/clients/gateway.py is available
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{gateway_url.rstrip('/')}/v1/embeddings",
            json={"model": EMBEDDING_MODEL_NAME, "input": [query]},
        )
        response.raise_for_status()

    payload = response.json()
    data = payload.get("data") or []
    if not data or "embedding" not in data[0]:
        raise ValueError("Inference Gateway returned an embeddings response without data[0].embedding")

    embedding = data[0]["embedding"]
    if not isinstance(embedding, list):
        raise ValueError("Inference Gateway returned a non-list embedding")

    return [float(value) for value in embedding]


def _build_should_filter(key: str, values: list[str] | None) -> Filter | None:
    if not values:
        return None

    return Filter(
        should=[
            FieldCondition(key=key, match=MatchAny(any=values))
        ]
    )


def _build_qdrant_filter(
    *,
    tickers: list[str] | None,
    sections: list[str] | None,
    filing_types: list[str] | None,
    date_range_start: str | None,
    date_range_end: str | None,
) -> Filter | None:
    must_conditions: list[Any] = []

    ticker_filter = _build_should_filter("ticker", tickers)
    if ticker_filter is not None:
        must_conditions.append(ticker_filter)

    section_filter = _build_should_filter("section", sections)
    if section_filter is not None:
        must_conditions.append(section_filter)

    if filing_types:
        must_conditions.append(
            FieldCondition(key="filing_type", match=MatchAny(any=filing_types))
        )

    if date_range_start is not None or date_range_end is not None:
        must_conditions.append(
            FieldCondition(
                key="filed_at",
                range=Range(gte=date_range_start, lte=date_range_end),
            )
        )

    if not must_conditions:
        return None
    return Filter(must=must_conditions)


async def vector_search(
    query: str,
    tickers: list[str] | None = None,
    sections: list[str] | None = None,
    filing_types: list[str] | None = None,
    date_range_start: str | None = None,
    date_range_end: str | None = None,
    k: int = 30,
    qdrant_url: str | None = None,
    gateway_url: str | None = None,
) -> list[EvidenceChunk]:
    """Embed the query through the gateway, search Qdrant, and apply plan metadata filters."""
    resolved_qdrant_url = _resolve_qdrant_url(qdrant_url)
    resolved_gateway_url = _resolve_gateway_url(gateway_url)
    collection_name = _resolve_qdrant_collection()

    query_vector = await _embed_query(query, resolved_gateway_url)
    query_filter = _build_qdrant_filter(
        tickers=tickers,
        sections=sections,
        filing_types=filing_types,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )

    client = AsyncQdrantClient(url=resolved_qdrant_url)
    try:
        results = await client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            with_payload=True,
            limit=k,
        )
    finally:
        await client.close()

    chunks: list[EvidenceChunk] = []
    for point in results:
        payload = point.payload or {}
        chunks.append(_payload_to_evidence_chunk(payload, score=float(point.score)))
    return chunks


async def execute_retrieval_plan(
    plan: RetrievalPlan,
    k: int = 30,
) -> list[EvidenceChunk]:
    """Execute both retrieval halves for a RetrievalPlan and return a temporary merged candidate set."""
    bm25_task = bm25_search(
        keywords=plan.bm25_keywords,
        tickers=plan.target_tickers,
        sections=plan.sections,
        filing_types=plan.filing_types,
        date_range_start=plan.date_range_start,
        date_range_end=plan.date_range_end,
        k=k,
    )
    vector_task = vector_search(
        query=plan.query,
        tickers=plan.target_tickers,
        sections=plan.sections,
        filing_types=plan.filing_types,
        date_range_start=plan.date_range_start,
        date_range_end=plan.date_range_end,
        k=k,
    )
    bm25_result, vector_result = await asyncio.gather(
        bm25_task,
        vector_task,
        return_exceptions=True,
    )

    bm25_chunks: list[EvidenceChunk] = []
    vector_chunks: list[EvidenceChunk] = []

    if isinstance(bm25_result, Exception):
        logger.warning("bm25_search failed during retrieval plan execution", exc_info=bm25_result)
    else:
        bm25_chunks = bm25_result

    if isinstance(vector_result, Exception):
        logger.warning("vector_search failed during retrieval plan execution", exc_info=vector_result)
    else:
        vector_chunks = vector_result

    # TODO: replace stub merge with RRF (Reciprocal Rank Fusion) + cross-encoder rerank via gateway + diversity filter
    merged_by_chunk_id: dict[str, EvidenceChunk] = {}
    for chunk in [*bm25_chunks, *vector_chunks]:
        existing = merged_by_chunk_id.get(chunk.chunk_id)
        if existing is None or chunk.rerank_score > existing.rerank_score:
            merged_by_chunk_id[chunk.chunk_id] = chunk

    return sorted(
        merged_by_chunk_id.values(),
        key=lambda chunk: chunk.rerank_score,
        reverse=True,
    )[:k]


async def hybrid_retrieve(
    query: str,
    ticker: str | None = None,
    section: str | None = None,
    k: int = 10,
) -> list[EvidenceChunk]:
    """Backward-compatible wrapper that builds a minimal RetrievalPlan and delegates to execute_retrieval_plan."""
    plan = RetrievalPlan(
        query=query,
        target_tickers=[ticker] if ticker else [],
        filing_types=["10-K", "10-Q"],
        sections=[section] if section else [],
        date_range_start="1900-01-01",
        date_range_end="9999-12-31",
        bm25_keywords=[query],
    )
    return await execute_retrieval_plan(plan, k=k)
