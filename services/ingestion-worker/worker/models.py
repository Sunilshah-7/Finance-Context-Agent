"""Internal ingestion pipeline models.

These Pydantic models describe the handoff between EDGAR discovery, SEC HTML
normalization, chunk creation, embedding, SQLite writes, and Qdrant upserts.
They are service-local pipeline shapes, not shared Agent API response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FilingRef(BaseModel):
    ticker: str
    cik: str
    company_name: str | None = None
    filing_type: str
    accession_number: str
    filed_at: str
    primary_document: str
    fiscal_period: str | None = None
    source_url: str | None = None


class NormalizedSection(BaseModel):
    section_id: str
    item_label: str
    title: str
    text: str
    tables: list[str] = Field(default_factory=list)
    word_count: int


class NormalizedDocument(BaseModel):
    document_id: str
    ticker: str
    cik: str
    company_name: str | None = None
    filing_type: str
    accession_number: str
    filed_at: str
    fiscal_period: str
    source_url: str
    sections: list[NormalizedSection] = Field(default_factory=list)
    local_path: str | None = None
    checksum: str | None = None


class ChunkInput(BaseModel):
    chunk_id: str
    document_id: str
    ticker: str
    cik: str
    company_name: str | None = None
    filing_type: str
    accession_number: str
    filed_at: str
    fiscal_period: str
    section: str
    item_label: str
    section_title: str
    chunk_index: int
    text: str
    text_hash: str
    token_count: int
    citation_anchor: str
    source_url: str
    is_table: bool = False


class ChunkWithEmbedding(ChunkInput):
    embedding: list[float]
