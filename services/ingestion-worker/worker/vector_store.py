"""Qdrant payload construction and vector upsert helpers.

The ingestion worker stores chunk text/metadata in SQLite and embeddings in the
``fincontext_chunks`` Qdrant collection. Payloads are built from the shared
schema contract so retrieval, memo generation, and citation cards see the same
field names.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import sys

from .models import ChunkWithEmbedding

try:
    from fincontext_schemas import QdrantChunkPayload
except ModuleNotFoundError:  # local Python may not have the editable package installed
    schema_src = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "python"
    sys.path.insert(0, str(schema_src))
    from db import QdrantChunkPayload  # type: ignore[no-redef]


DEFAULT_COLLECTION = "fincontext_chunks"


def build_payload(chunk: ChunkWithEmbedding) -> QdrantChunkPayload:
    return QdrantChunkPayload(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        ticker=chunk.ticker,
        cik=chunk.cik,
        company_name=chunk.company_name,
        filing_type=chunk.filing_type,
        accession_number=chunk.accession_number,
        filed_at=chunk.filed_at,
        fiscal_period=chunk.fiscal_period,
        section=chunk.section,
        item_label=chunk.item_label,
        section_title=chunk.section_title,
        chunk_index=chunk.chunk_index,
        token_count=chunk.token_count,
        text=chunk.text,
        text_hash=chunk.text_hash,
        citation_anchor=chunk.citation_anchor,
        source_url=chunk.source_url,
        is_table=chunk.is_table,
    )


def upsert_vectors(
    chunks: Iterable[ChunkWithEmbedding],
    *,
    qdrant_url: str,
    collection: str = DEFAULT_COLLECTION,
) -> int:
    chunk_list = list(chunks)
    if not chunk_list:
        return 0

    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    client = QdrantClient(url=qdrant_url)
    client.upsert(
        collection_name=collection,
        points=[
            PointStruct(
                id=chunk.chunk_id,
                vector=chunk.embedding,
                payload=build_payload(chunk).model_dump(exclude_none=True),
            )
            for chunk in chunk_list
        ],
    )
    return len(chunk_list)
