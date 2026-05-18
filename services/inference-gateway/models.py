from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class BackendRoute:
    model_name: str
    upstream_base_url: str
    upstream_path: str
    upstream_model_name: str | None = None

    @property
    def url(self) -> str:
        return f"{self.upstream_base_url.rstrip('/')}{self.upstream_path}"


class HealthCheckResult(BaseModel):
    name: str
    status: str
    url: str
    detail: str | None = None


class RequestMetric(BaseModel):
    endpoint: str
    model: str
    status_code: int
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    time_to_first_token_ms: float | None = None
    tokens_per_second: float | None = None


class MetricsSummary(BaseModel):
    count: int = 0
    avg_input_tokens: float | None = None
    avg_output_tokens: float | None = None
    avg_time_to_first_token_ms: float | None = None
    avg_total_latency_ms: float | None = None
    avg_tokens_per_second: float | None = None


class MetricsResponse(BaseModel):
    models: dict[str, MetricsSummary] = Field(default_factory=dict)
    recent_requests: int = 0
    by_endpoint: dict[str, int] = Field(default_factory=dict)
    raw: list[dict[str, Any]] = Field(default_factory=list)
