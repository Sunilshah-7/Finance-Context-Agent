from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .state import AnalystMemo, DisclosureChange, RiskScore


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool
    request_id: str


class ApiErrorEnvelope(BaseModel):
    error: ApiError


class HealthResponse(BaseModel):
    status: str
    gpu: str | None = None
    vllm_72b: str | None = None
    vllm_14b: str | None = None
    qdrant: str | None = None
    chunks_indexed: int | None = None


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
    analysis_type: Literal["latest_filings", "portfolio_review", "custom_question"] = "latest_filings"
    question: str | None = None


class AnalyzeResponse(BaseModel):
    job_id: str
    portfolio_id: str
    status: str
    created_at: str


class JobStatusResponse(BaseModel):
    job_id: str
    portfolio_id: str | None = None
    status: str
    stage: str | None = None
    progress: float = 0.0
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: int | None = None
    citation_pass_rate: float | None = None
    findings_count: int | None = None
    error: str | None = None


class FindingsResponse(BaseModel):
    portfolio_id: str
    job_id: str
    analyzed_at: str | None = None
    risk_scores: list[RiskScore] = Field(default_factory=list)
    memo: AnalystMemo | None = None


class DiffResponse(BaseModel):
    ticker: str
    section: str
    filing_type: str
    year_a: str
    year_b: str
    changes: list[DisclosureChange] = Field(default_factory=list)


class ModelMetric(BaseModel):
    count: int
    avg_input_tokens: float | None = None
    avg_output_tokens: float | None = None
    avg_time_to_first_token_ms: float | None = None
    avg_total_latency_ms: float | None = None
    avg_tokens_per_second: float | None = None


class BenchmarkMetricsResponse(BaseModel):
    models: dict[str, ModelMetric] = Field(default_factory=dict)
    gpu: dict[str, Any] = Field(default_factory=dict)
