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
from qdrant_client.models import FieldCondition, Filter, MatchValue

try:
    from fincontext_schemas import EvidenceChunk
except ModuleNotFoundError:  # local Python may not have the editable package installed
    schema_src = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "python"
    sys.path.insert(0, str(schema_src))
    from state import EvidenceChunk  # type: ignore[no-redef]


logger = logging.getLogger(__name__)

DEFAULT_QDRANT_COLLECTION = "fincontext_chunks"
DEFAULT_SQLITE_PATH = "./fincontext.db"
DEFAULT_GATEWAY_URL = "http://localhost:8080"
EMBEDDING_MODEL_NAME = "fincontext-embedding"
_gateway_clients: dict[str, httpx.AsyncClient] = {}


def _resolve_sqlite_path(sqlite_path: str | None) -> str:
    return sqlite_path or os.getenv("SQLITE_DB_PATH", DEFAULT_SQLITE_PATH)


def _resolve_qdrant_url(qdrant_url: str | None) -> str:
    return qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")


def _resolve_gateway_url(gateway_url: str | None) -> str:
    return gateway_url or os.getenv("INFERENCE_GATEWAY_URL", DEFAULT_GATEWAY_URL)


def _resolve_qdrant_collection() -> str:
    return os.getenv("QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION)


def _escape_fts5_query(query: str) -> str:
    """Convert free-form user text into a safe FTS5 MATCH expression."""
    tokens: list[str] = []
    current: list[str] = []

    for char in query:
        if char.isalnum() or char in {"_", "-"}:
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current = []

    if current:
        tokens.append("".join(current))

    if not tokens:
        return '""'

    return " ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


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


def _build_bm25_sql(section: str | None, ticker: str | None) -> tuple[str, list[Any]]:
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

    if ticker is not None:
        sql += " AND c.ticker = ?"
        params.append(ticker)

    if section is not None:
        sql += " AND c.section = ?"
        params.append(section)

    sql += " ORDER BY bm25_score ASC LIMIT ?"
    return sql, params


def _run_bm25_query(
    *,
    query: str,
    ticker: str | None,
    section: str | None,
    k: int,
    sqlite_path: str,
) -> list[EvidenceChunk]:
    match_query = _escape_fts5_query(query)
    sql, extra_params = _build_bm25_sql(section=section, ticker=ticker)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, [match_query, *extra_params, k]).fetchall()
    finally:
        conn.close()

    return [
        _row_to_evidence_chunk(row, score=-float(row["bm25_score"]))
        for row in rows
    ]


async def bm25_search(
    query: str,
    ticker: str | None = None,
    section: str | None = None,
    k: int = 20,
    sqlite_path: str | None = None,
) -> list[EvidenceChunk]:
    """Run SQLite FTS5 BM25 retrieval and normalize rows into EvidenceChunk objects."""
    resolved_sqlite_path = _resolve_sqlite_path(sqlite_path)
    return await asyncio.to_thread(
        _run_bm25_query,
        query=query,
        ticker=ticker,
        section=section,
        k=k,
        sqlite_path=resolved_sqlite_path,
    )


def _get_gateway_client(gateway_url: str) -> httpx.AsyncClient:
    normalized_gateway_url = gateway_url.rstrip("/")
    client = _gateway_clients.get(normalized_gateway_url)
    if client is None:
        client = httpx.AsyncClient(base_url=normalized_gateway_url, timeout=30.0)
        _gateway_clients[normalized_gateway_url] = client
    return client


async def _embed_query(query: str, gateway_url: str) -> list[float]:
    client = _get_gateway_client(gateway_url)
    response = await client.post(
        "/v1/embeddings",
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


async def vector_search(
    query: str,
    ticker: str | None = None,
    section: str | None = None,
    k: int = 20,
    qdrant_url: str | None = None,
    gateway_url: str | None = None,
) -> list[EvidenceChunk]:
    """Embed the query through the gateway, search Qdrant, and return EvidenceChunk hits."""
    resolved_qdrant_url = _resolve_qdrant_url(qdrant_url)
    resolved_gateway_url = _resolve_gateway_url(gateway_url)
    collection_name = _resolve_qdrant_collection()

    query_vector = await _embed_query(query, resolved_gateway_url)

    must_conditions: list[FieldCondition] = []
    if ticker is not None:
        must_conditions.append(FieldCondition(key="ticker", match=MatchValue(value=ticker)))
    if section is not None:
        must_conditions.append(FieldCondition(key="section", match=MatchValue(value=section)))

    query_filter = Filter(must=must_conditions) if must_conditions else None

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


async def hybrid_retrieve(
    query: str,
    ticker: str | None = None,
    section: str | None = None,
    k: int = 10,
) -> list[EvidenceChunk]:
    """Run BM25 and vector retrieval in parallel, then apply a temporary score-based merge."""
    bm25_task = bm25_search(query=query, ticker=ticker, section=section, k=k * 2)
    vector_task = vector_search(query=query, ticker=ticker, section=section, k=k * 2)
    bm25_result, vector_result = await asyncio.gather(
        bm25_task,
        vector_task,
        return_exceptions=True,
    )

    bm25_chunks: list[EvidenceChunk] = []
    vector_chunks: list[EvidenceChunk] = []

    if isinstance(bm25_result, Exception):
        logger.warning("bm25_search failed during hybrid retrieval", exc_info=bm25_result)
    else:
        bm25_chunks = bm25_result

    if isinstance(vector_result, Exception):
        logger.warning("vector_search failed during hybrid retrieval", exc_info=vector_result)
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
