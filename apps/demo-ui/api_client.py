"""Agent API client for the FinContext Gradio demo.

This module is the only network boundary in the demo UI. It talks to the
Agent API over HTTP(S), adds the optional bearer token, and converts connection
or API errors into small result objects that the Gradio views can render without
crashing. It never calls Qdrant, SQLite, vLLM, TEI, or the Inference Gateway
directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


DEFAULT_AGENT_API_URL = "http://localhost:8090"
DEFAULT_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class ApiResult:
    """Small transport result used by UI code to render success or failure."""

    ok: bool
    data: dict[str, Any] | list[Any] | None = None
    message: str = ""
    status_code: int | None = None


class AgentApiClient:
    """Thin synchronous wrapper around the documented Agent API endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = normalize_base_url(base_url or os.getenv("AGENT_API_URL", DEFAULT_AGENT_API_URL))
        self.api_key = api_key if api_key is not None else os.getenv("AGENT_API_KEY", "")
        self.timeout_seconds = timeout_seconds

    def health(self) -> ApiResult:
        return self._request("GET", "/health", auth=False)

    def upload_portfolio(self, file_path: str | Path, name: str = "Demo Portfolio") -> ApiResult:
        path = Path(file_path)
        if not path.exists():
            return ApiResult(False, message=f"Portfolio CSV not found: {path}")
        try:
            with path.open("rb") as handle:
                files = {"file": (path.name, handle, "text/csv")}
                data = {"name": name}
                return self._request("POST", "/api/portfolio/upload", data=data, files=files)
        except OSError as exc:
            return ApiResult(False, message=f"Could not read portfolio CSV: {exc}")

    def start_analysis(
        self,
        portfolio_id: str,
        question: str | None = None,
        analysis_type: str = "latest_filings",
    ) -> ApiResult:
        payload: dict[str, Any] = {
            "portfolio_id": portfolio_id.strip(),
            "analysis_type": analysis_type,
            "question": question.strip() if question else None,
        }
        if payload["question"]:
            payload["analysis_type"] = "custom_question"
        return self._request("POST", "/api/analyze", json=payload)

    def get_job(self, job_id: str) -> ApiResult:
        return self._request("GET", f"/api/jobs/{job_id.strip()}")

    def get_findings(self, portfolio_id: str, job_id: str | None = None) -> ApiResult:
        params = {"job_id": job_id.strip()} if job_id else None
        return self._request("GET", f"/api/findings/{portfolio_id.strip()}", params=params)

    def get_diff(
        self,
        ticker: str,
        section: str | None = None,
        year_a: str | None = None,
        year_b: str | None = None,
        filing_type: str = "10-K",
    ) -> ApiResult:
        params = {"filing_type": filing_type}
        if section:
            params["section"] = section
        if year_a:
            params["year_a"] = year_a
        if year_b:
            params["year_b"] = year_b
        return self._request("GET", f"/api/diff/{ticker.strip().upper()}", params=params)

    def get_documents(self, ticker: str) -> ApiResult:
        return self._request("GET", f"/api/documents/{ticker.strip().upper()}")

    def get_benchmark_metrics(self) -> ApiResult:
        return self._request("GET", "/api/benchmark/metrics")

    def _request(self, method: str, path: str, auth: bool = True, **kwargs: Any) -> ApiResult:
        headers = dict(kwargs.pop("headers", {}) or {})
        if auth and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(method, self._url(path), headers=headers, **kwargs)
        except httpx.ConnectError:
            return ApiResult(False, message=f"Agent API is unreachable at {self.base_url}")
        except httpx.TimeoutException:
            return ApiResult(False, message=f"Agent API timed out after {self.timeout_seconds:.0f}s")
        except httpx.HTTPError as exc:
            return ApiResult(False, message=f"Agent API request failed: {exc}")

        try:
            payload: dict[str, Any] | list[Any] | None = response.json()
        except ValueError:
            payload = None

        if response.is_success:
            return ApiResult(True, data=payload, status_code=response.status_code)

        return ApiResult(
            False,
            data=payload,
            message=extract_error_message(payload) or f"Agent API returned HTTP {response.status_code}",
            status_code=response.status_code,
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"


def normalize_base_url(value: str) -> str:
    """Normalize configured URLs so endpoint joins are predictable."""

    cleaned = value.strip() or DEFAULT_AGENT_API_URL
    return cleaned.rstrip("/")


def extract_error_message(payload: dict[str, Any] | list[Any] | None) -> str:
    """Read the standard API error shape without assuming every response has it."""

    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return ""
