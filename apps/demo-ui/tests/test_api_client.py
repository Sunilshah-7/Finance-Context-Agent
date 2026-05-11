"""Focused tests for the Gradio UI Agent API client.

These tests avoid Gradio and live services. They verify the small transport
contract the UI relies on: URL normalization, bearer auth, standard API errors,
and multipart portfolio uploads.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from api_client import AgentApiClient, extract_error_message, normalize_base_url  # noqa: E402


def test_normalize_base_url_strips_trailing_slash() -> None:
    assert normalize_base_url("http://localhost:8090/") == "http://localhost:8090"


def test_extract_error_message_reads_standard_shape() -> None:
    payload = {"error": {"message": "CSV is missing required columns"}}
    assert extract_error_message(payload) == "CSV is missing required columns"


def test_health_omits_authorization_header(monkeypatch) -> None:
    seen_headers: dict[str, str] = {}
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(200, json={"status": "ok"})

    monkeypatch.setattr(httpx, "Client", lambda timeout: original_client(transport=httpx.MockTransport(handler)))
    result = AgentApiClient(api_key="secret").health()

    assert result.ok is True
    assert "authorization" not in seen_headers


def test_upload_portfolio_sends_bearer_auth_and_multipart(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "portfolio.csv"
    csv_path.write_text("ticker,shares,market_value,sector\nAMD,1,100,Semiconductors\n")
    seen: dict[str, str] = {}
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization", "")
        seen["content_type"] = request.headers.get("content-type", "")
        body = request.read().decode()
        seen["body"] = body
        return httpx.Response(200, json={"portfolio_id": "p_demo", "status": "created"})

    monkeypatch.setattr(httpx, "Client", lambda timeout: original_client(transport=httpx.MockTransport(handler)))
    result = AgentApiClient(api_key="secret").upload_portfolio(csv_path, "Demo Portfolio")

    assert result.ok is True
    assert seen["authorization"] == "Bearer secret"
    assert "multipart/form-data" in seen["content_type"]
    assert "Demo Portfolio" in seen["body"]
    assert "AMD,1,100,Semiconductors" in seen["body"]
