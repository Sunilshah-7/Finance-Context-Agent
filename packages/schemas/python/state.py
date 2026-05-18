from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ChangeType = Literal[
    "new_risk",
    "removed_risk",
    "intensified_language",
    "softened_language",
    "metric_changed",
    "legal_accounting_update",
]


class Holding(BaseModel):
    ticker: str
    name: str
    weight: float
    sector: str
    shares: float
    avg_cost: float


class RetrievalPlan(BaseModel):
    query: str
    target_tickers: list[str]
    filing_types: list[str]
    sections: list[str]
    date_range_start: str
    date_range_end: str
    bm25_keywords: list[str]


class Citation(BaseModel):
    chunk_id: str
    citation_anchor: str
    source_url: str
    filed_at: str
    ticker: str
    filing_type: str
    section: str


class EvidenceChunk(BaseModel):
    chunk_id: str
    document_id: str
    ticker: str
    filing_type: str
    filed_at: str
    section: str
    item_label: str
    text: str
    citation_anchor: str
    source_url: str
    chunk_index: int
    rerank_score: float


class DisclosureChange(BaseModel):
    ticker: str
    section: str
    change_type: ChangeType
    old_citation: Optional[Citation] = None
    new_citation: Optional[Citation] = None
    summary: str
    severity: float
    confidence: float


class RiskScore(BaseModel):
    ticker: str
    score: float
    delta: float
    confidence: float
    top_drivers: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    portfolio_impact: str


class AnalystMemo(BaseModel):
    executive_summary: str
    affected_holdings: list[str] = Field(default_factory=list)
    disclosure_changes: list[DisclosureChange] = Field(default_factory=list)
    risk_scores: list[RiskScore] = Field(default_factory=list)
    evidence_table: list[Citation] = Field(default_factory=list)
    watchlist_questions: list[str] = Field(default_factory=list)
    limitations: str
    disclaimer: str
    citation_pass_rate: float


class AnalysisState(BaseModel):
    user_id: str
    portfolio_id: str
    question: Optional[str] = None

    # After node 1: portfolio_context_planner
    holdings: list[Holding] = Field(default_factory=list)
    target_tickers: list[str] = Field(default_factory=list)
    retrieval_plan: Optional[RetrievalPlan] = None

    # After node 2: filing_retrieval
    retrieved_chunks: list[EvidenceChunk] = Field(default_factory=list)

    # After node 3: disclosure_change
    disclosure_changes: list[DisclosureChange] = Field(default_factory=list)

    # After node 4: analyst_memo
    risk_scores: list[RiskScore] = Field(default_factory=list)
    memo: Optional[AnalystMemo] = None
    citation_pass_rate: Optional[float] = None

    error: Optional[str] = None
    partial: bool = False
