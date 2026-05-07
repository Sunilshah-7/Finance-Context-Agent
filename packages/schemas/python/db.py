from __future__ import annotations

from typing import ClassVar, Optional

from pydantic import BaseModel


class PortfolioRow(BaseModel):
    table_name: ClassVar[str] = "portfolios"

    id: str
    name: str
    base_currency: str = "USD"
    created_at: str


class HoldingRow(BaseModel):
    table_name: ClassVar[str] = "holdings"

    id: str
    portfolio_id: str
    ticker: str
    market_value: float
    company_name: Optional[str] = None
    cik: Optional[str] = None
    shares: Optional[float] = None
    cost_basis: Optional[float] = None
    sector: Optional[str] = None
    weight: Optional[float] = None
    created_at: str


class DocumentRow(BaseModel):
    table_name: ClassVar[str] = "documents"

    id: str
    ticker: str
    filing_type: str
    created_at: str
    cik: Optional[str] = None
    company_name: Optional[str] = None
    accession_number: Optional[str] = None
    filed_at: Optional[str] = None
    fiscal_period: Optional[str] = None
    source_url: Optional[str] = None
    local_path: Optional[str] = None
    sections_parsed: Optional[str] = None  # JSON array stored as text
    checksum: Optional[str] = None


class ChunkRow(BaseModel):
    table_name: ClassVar[str] = "chunks"

    id: str  # UUID, same value as Qdrant point ID (vector_id)
    document_id: str
    ticker: str
    filing_type: str
    filed_at: str
    section: str
    text: str
    text_hash: str
    citation_anchor: str
    chunk_index: int
    created_at: str
    item_label: Optional[str] = None
    section_title: Optional[str] = None
    token_count: Optional[int] = None
    source_url: Optional[str] = None
    is_table: int = 0
    vector_id: Optional[str] = None


class AnalysisJobRow(BaseModel):
    table_name: ClassVar[str] = "analysis_jobs"

    id: str
    portfolio_id: str
    job_type: str  # portfolio_review | custom_question | latest_filings
    created_at: str
    status: str = "queued"  # queued | running | completed | failed
    progress: float = 0.0
    stage: Optional[str] = None  # planning | retrieving | analyzing | writing | complete
    question: Optional[str] = None
    citation_pass_rate: Optional[float] = None
    findings_count: Optional[int] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class FindingRow(BaseModel):
    table_name: ClassVar[str] = "findings"

    id: str
    portfolio_id: str
    job_id: str
    ticker: str
    severity: str      # none | low | medium | high | critical
    risk_category: str
    summary: str
    evidence_json: str  # JSON: list of {citation_anchor, text, source_url}
    created_at: str
    holding_id: Optional[str] = None
    risk_score: Optional[float] = None
    score_delta: Optional[float] = None
    confidence: Optional[float] = None
