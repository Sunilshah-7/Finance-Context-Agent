from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class BackendRoute:
    # Simple routing contract used only inside the gateway layer.
    model_name: str
    upstream_base_url: str
    upstream_path: str

    @property
    def url(self) -> str:
        return f"{self.upstream_base_url.rstrip('/')}{self.upstream_path}"


class HealthCheckResult(BaseModel):
    # Returned by GET /health; downstream infra/debug tooling should treat this as read-only input.
    name: str
    status: str
    url: str
    detail: str | None = None


class RequestMetric(BaseModel):
    # Internal metric record captured per request before being rolled up for benchmarks.
    endpoint: str
    model: str
    status_code: int
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    time_to_first_token_ms: float | None = None
    tokens_per_second: float | None = None


class MetricsSummary(BaseModel):
    # Summary row consumed by benchmark/debug surfaces.
    count: int = 0
    avg_input_tokens: float | None = None
    avg_output_tokens: float | None = None
    avg_time_to_first_token_ms: float | None = None
    avg_total_latency_ms: float | None = None
    avg_tokens_per_second: float | None = None


class MetricsResponse(BaseModel):
    # Gateway metrics response contract for later Agent API + Gradio integration.
    models: dict[str, MetricsSummary] = Field(default_factory=dict)
    recent_requests: int = 0
    by_endpoint: dict[str, int] = Field(default_factory=dict)
    raw: list[dict[str, Any]] = Field(default_factory=list)
