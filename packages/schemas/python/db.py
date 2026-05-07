from __future__ import annotations

from pydantic import BaseModel


class PortfolioRow(BaseModel):
    id: str
    name: str
    base_currency: str = "USD"
    created_at: str


class HoldingRow(BaseModel):
    id: str
    portfolio_id: str
    ticker: str
    company_name: str | None = None
    cik: str | None = None
    shares: float | None = None
    market_value: float
    cost_basis: float | None = None
    sector: str | None = None
    weight: float | None = None
    created_at: str


class DocumentRow(BaseModel):
    id: str
    ticker: str
    cik: str | None = None
    company_name: str | None = None
    filing_type: str
    accession_number: str | None = None
    filed_at: str | None = None
    fiscal_period: str | None = None
    source_url: str | None = None
    local_path: str | None = None
    sections_parsed: str | None = None
    checksum: str | None = None
    created_at: str


class ChunkRow(BaseModel):
    id: str
    document_id: str
    ticker: str
    filing_type: str
    filed_at: str
    section: str
    item_label: str | None = None
    section_title: str | None = None
    chunk_index: int
    text: str
    text_hash: str
    token_count: int | None = None
    citation_anchor: str
    source_url: str | None = None
    is_table: int = 0
    vector_id: str | None = None
    created_at: str


class AnalysisJobRow(BaseModel):
    id: str
    portfolio_id: str
    job_type: str
    status: str
    stage: str | None = None
    progress: float = 0.0
    question: str | None = None
    citation_pass_rate: float | None = None
    findings_count: int | None = None
    error: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class FindingRow(BaseModel):
    id: str
    portfolio_id: str
    job_id: str
    holding_id: str | None = None
    ticker: str
    severity: str
    risk_category: str
    summary: str
    evidence_json: str
    risk_score: float | None = None
    score_delta: float | None = None
    confidence: float | None = None
    created_at: str


class DisclosureChangeRow(BaseModel):
    id: str
    job_id: str
    ticker: str
    section: str
    filing_type: str
    year_a: str
    year_b: str
    change_type: str
    materiality: str
    confidence: float
    summary: str
    old_text: str | None = None
    new_text: str | None = None
    old_citation_anchor: str | None = None
    new_citation_anchor: str | None = None
    old_source_url: str | None = None
    new_source_url: str | None = None
    created_at: str
