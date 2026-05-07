from __future__ import annotations

from typing import Literal, Optional, TypeAlias, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Error shape (all services)
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Benchmark sub-models
# ---------------------------------------------------------------------------


class GpuInfo(BaseModel):
    device: str
    vram_gb: float
    vram_used_gb: float


class VllmMetrics(BaseModel):
    count: int
    avg_input_tokens: float
    avg_output_tokens: float
    avg_time_to_first_token_ms: float
    avg_total_latency_ms: float
    avg_tokens_per_second: float


class EmbeddingMetrics(BaseModel):
    count: int
    avg_batch_size: int
    avg_latency_ms: float


class RerankerMetrics(BaseModel):
    count: int
    avg_candidates: int
    avg_latency_ms: float


class RecentRequests(BaseModel):
    vllm_72b: VllmMetrics
    vllm_14b: VllmMetrics
    embedding: EmbeddingMetrics
    reranker: RerankerMetrics


class BenchmarkScenarios(BaseModel):
    single_10k_analysis_seconds: float
    five_stock_portfolio_seconds: float
    interactive_qa_seconds: float


# ---------------------------------------------------------------------------
# Findings sub-models (API response shape differs from internal state types)
# ---------------------------------------------------------------------------


class RiskDriver(BaseModel):
    category: str
    score: float
    summary: str
    citation: str


class PortfolioImpact(BaseModel):
    holding_weight: float
    sector_weight: float
    exposure_level: str


class FindingsRiskScore(BaseModel):
    ticker: str
    overall_score: float
    score_delta: float
    confidence: float
    drivers: list[RiskDriver] = Field(default_factory=list)
    portfolio_impact: PortfolioImpact


class PortfolioExposure(BaseModel):
    ticker: str
    weight: float
    exposure_level: str


class EvidenceEntry(BaseModel):
    citation_id: str
    citation_anchor: str
    source_url: str


class DisclosureChangeSummary(BaseModel):
    ticker: str
    section: str
    change_type: str
    materiality: str
    summary: str
    new_citation: str
    old_citation_anchor: Optional[str] = None
    new_citation_anchor: Optional[str] = None
    old_source_url: Optional[str] = None
    new_source_url: Optional[str] = None


class FindingsMemo(BaseModel):
    executive_summary: str
    portfolio_exposure_affected: list[PortfolioExposure] = Field(default_factory=list)
    top_disclosure_changes: list[DisclosureChangeSummary] = Field(default_factory=list)
    evidence_table: list[EvidenceEntry] = Field(default_factory=list)
    watchlist_questions: list[str] = Field(default_factory=list)
    limitations: str
    confidence: float
    disclaimer: str


# ---------------------------------------------------------------------------
# Diff sub-model
# ---------------------------------------------------------------------------


class DiffChange(BaseModel):
    change_type: str
    materiality: str
    confidence: float
    summary: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    old_citation_anchor: Optional[str] = None
    new_citation_anchor: Optional[str] = None
    old_source_url: Optional[str] = None
    new_source_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Document explorer sub-models
# ---------------------------------------------------------------------------


class DocumentSummary(BaseModel):
    document_id: str
    filing_type: str
    filed_at: str
    accession_number: Optional[str] = None
    source_url: Optional[str] = None
    sections_parsed: list[str] = Field(default_factory=list)
    chunks_indexed: int


# ---------------------------------------------------------------------------
# Chat SSE event sub-models
# ---------------------------------------------------------------------------


class ChatStageEvent(BaseModel):
    type: Literal["stage"] = "stage"
    stage: Literal["planning", "retrieving", "analyzing", "writing", "complete"]


class ChatTokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class ChatCitation(BaseModel):
    citation_anchor: str
    chunk_id: str
    source_url: str


class ChatCitationsEvent(BaseModel):
    type: Literal["citations"] = "citations"
    citations: list[ChatCitation] = Field(default_factory=list)


class ChatDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    citation_pass_rate: float


ChatStreamEvent: TypeAlias = Union[
    ChatStageEvent,
    ChatTokenEvent,
    ChatCitationsEvent,
    ChatDoneEvent,
]


# ---------------------------------------------------------------------------
# Primary request / response models
# ---------------------------------------------------------------------------


class PortfolioUploadResponse(BaseModel):
    portfolio_id: str
    name: str
    holdings_count: int
    total_value: float
    tickers: list[str] = Field(default_factory=list)
    missing_cik: list[str] = Field(default_factory=list)
    status: str


class AnalyzeRequest(BaseModel):
    portfolio_id: str
    analysis_type: Literal["latest_filings", "portfolio_review", "custom_question"] = (
        "latest_filings"
    )
    question: Optional[str] = None


class AnalyzeResponse(BaseModel):
    job_id: str
    portfolio_id: str
    status: str
    created_at: str


class JobStatusResponse(BaseModel):
    job_id: str
    portfolio_id: str
    status: str
    created_at: str
    stage: Optional[str] = None
    progress: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    citation_pass_rate: Optional[float] = None
    findings_count: Optional[int] = None


class FindingsResponse(BaseModel):
    portfolio_id: str
    job_id: str
    analyzed_at: str
    risk_scores: list[FindingsRiskScore] = Field(default_factory=list)
    memo: FindingsMemo


class DiffResponse(BaseModel):
    ticker: str
    section: str
    filing_type: str
    year_a: str
    year_b: str
    changes: list[DiffChange] = Field(default_factory=list)


class DocumentsResponse(BaseModel):
    ticker: str
    documents: list[DocumentSummary] = Field(default_factory=list)


class ChatRequest(BaseModel):
    portfolio_id: str
    question: str


class BenchmarkMetricsResponse(BaseModel):
    gpu_info: GpuInfo
    recent_requests: RecentRequests
    benchmark_scenarios: BenchmarkScenarios
