from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Holding(BaseModel):
    holding_id: str
    ticker: str
    company_name: str = ""
    cik: str = ""
    shares: float = 0.0
    market_value: float = 0.0
    weight: float = 0.0
    sector: str = ""


class RetrievalPlan(BaseModel):
    queries: list[str] = Field(default_factory=list)
    filing_types: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    date_range_start: str
    date_range_end: str
    comparison_pairs: list[tuple[str, str]] = Field(default_factory=list)


class EvidenceChunk(BaseModel):
    chunk_id: str
    document_id: str
    ticker: str
    filing_type: str
    filed_at: str
    section: str
    text: str
    citation_anchor: str
    retrieval_score: float = 0.0
    source_url: str


class DisclosureChange(BaseModel):
    ticker: str
    section: str
    change_type: Literal[
        "new_risk",
        "removed_risk",
        "intensified_language",
        "softened_language",
        "metric_changed",
        "legal_accounting_update",
        "boilerplate",
    ]
    summary: str
    old_text: str | None = None
    new_text: str | None = None
    old_citation_anchor: str | None = None
    new_citation_anchor: str | None = None
    materiality: Literal["low", "medium", "high"] = "medium"
    confidence: float = 0.0


class RiskDriver(BaseModel):
    category: str
    score: float
    summary: str
    citations: list[str] = Field(default_factory=list)


class RiskScore(BaseModel):
    ticker: str
    overall_score: float
    score_delta: float = 0.0
    confidence: float = 0.0
    drivers: list[RiskDriver] = Field(default_factory=list)
    portfolio_impact: dict[str, float | str] = Field(default_factory=dict)


class Citation(BaseModel):
    citation_id: str
    citation_anchor: str
    chunk_id: str
    document_id: str
    ticker: str
    source_url: str | None = None


class AnalystMemo(BaseModel):
    executive_summary: str
    portfolio_exposure_affected: list[dict[str, str | float]] = Field(default_factory=list)
    top_disclosure_changes: list[dict[str, str | float]] = Field(default_factory=list)
    risk_score_changes: list[dict[str, str | float]] = Field(default_factory=list)
    evidence_table: list[Citation] = Field(default_factory=list)
    watchlist_questions: list[str] = Field(default_factory=list)
    limitations: str
    confidence: float = 0.0
    disclaimer: str


class AnalysisState(BaseModel):
    user_id: str
    portfolio_id: str
    question: str | None = None
    holdings: list[Holding] = Field(default_factory=list)
    target_tickers: list[str] = Field(default_factory=list)
    retrieval_plan: RetrievalPlan | None = None
    retrieved_chunks: list[EvidenceChunk] = Field(default_factory=list)
    disclosure_changes: list[DisclosureChange] = Field(default_factory=list)
    risk_scores: list[RiskScore] = Field(default_factory=list)
    memo: AnalystMemo | None = None
    citation_pass_rate: float | None = None
    error: str | None = None
    partial: bool = False
