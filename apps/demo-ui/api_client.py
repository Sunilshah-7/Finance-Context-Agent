from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
import pandas as pd


class AgentApiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("AGENT_API_URL", "http://localhost:8090")).rstrip("/")
        self.api_key = api_key or os.getenv("AGENT_API_KEY", "")

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        return headers

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def upload_portfolio(self, name: str, file_obj: str | Path) -> dict[str, Any]:
        with open(file_obj, "rb") as handle:
            files = {"file": (Path(file_obj).name, handle, "text/csv")}
            return self._request("POST", "/api/portfolio/upload", data={"name": name}, files=files)

    def analyze(self, portfolio_id: str, analysis_type: str, question: str | None) -> dict[str, Any]:
        payload = {"portfolio_id": portfolio_id, "analysis_type": analysis_type, "question": question or None}
        return self._request("POST", "/api/analyze", json=payload)

    def job_status(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/jobs/{job_id}")

    def findings(self, portfolio_id: str, job_id: str | None = None) -> dict[str, Any]:
        params = {"job_id": job_id} if job_id else None
        return self._request("GET", f"/api/findings/{portfolio_id}", params=params)

    def diff(self, ticker: str, section: str, year_a: str, year_b: str, filing_type: str = "10-K") -> dict[str, Any]:
        params = {"section": section, "year_a": year_a, "year_b": year_b, "filing_type": filing_type}
        return self._request("GET", f"/api/diff/{ticker}", params=params)

    def documents(self, ticker: str) -> dict[str, Any]:
        return self._request("GET", f"/api/documents/{ticker}")

    def benchmark_metrics(self) -> dict[str, Any]:
        return self._request("GET", "/api/benchmark/metrics")

    def stream_chat(self, portfolio_id: str, question: str) -> Generator[str, None, None]:
        payload = {"portfolio_id": portfolio_id, "question": question}
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload,
            headers=self._headers,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            content = ""
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event.get("type") == "token":
                    content += event.get("text", "")
                    yield content
                if event.get("type") == "complete":
                    return

    def holdings_dataframe(self, upload_response: dict[str, Any]) -> pd.DataFrame:
        return pd.DataFrame({"ticker": upload_response.get("tickers", [])})

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, headers=self._headers, timeout=60.0) as client:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
