from __future__ import annotations

import json
from pathlib import Path
import sys

import httpx
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main import app  # noqa: E402
from models import BackendRoute  # noqa: E402
import router as gateway_router  # noqa: E402


def make_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/chat/completions"):
            payload = {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            }
            return httpx.Response(200, json=payload)
        if path.endswith("/v1/embeddings"):
            payload = {"data": [{"embedding": [0.1, 0.2, 0.3], "index": 0}], "usage": {"prompt_tokens": 3}}
            return httpx.Response(200, json=payload)
        if path.endswith("/v1/rerank"):
            payload = {"results": [{"index": 0, "relevance_score": 0.99}]}
            return httpx.Response(200, json=payload)
        if path.endswith("/health"):
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


def make_capture_transport(captured: list[dict[str, object]]):
    """Record upstream requests so routing, headers, and payloads can be asserted."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(
            {
                "path": request.url.path,
                "headers": dict(request.headers),
                "json": json.loads(request.content.decode("utf-8") or "{}"),
            }
        )
        path = request.url.path
        if path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )
        if path.endswith("/v1/embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [0.1], "index": 0}]})
        if path.endswith("/v1/rerank"):
            return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.9}]})
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


def test_chat_proxy_routes_to_reasoner():
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_transport())
        response = client.post(
            "/v1/chat/completions",
            json={"model": "fincontext-reasoner", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "ok"


def test_local_chat_keeps_internal_model_alias(monkeypatch):
    monkeypatch.delenv("NIM_API_KEY", raising=False)
    monkeypatch.setattr(
        gateway_router,
        "CHAT_MODEL_ROUTES",
        {
            "fincontext-planner": BackendRoute(
                model_name="fincontext-planner",
                upstream_base_url="http://localhost:8001/v1",
                upstream_path="/chat/completions",
            )
        },
    )
    captured: list[dict[str, object]] = []
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_capture_transport(captured))
        response = client.post(
            "/v1/chat/completions",
            json={"model": "fincontext-planner", "messages": [{"role": "user", "content": "plan"}]},
        )
        assert response.status_code == 200

    forwarded = captured[0]
    assert forwarded["json"]["model"] == "fincontext-planner"
    assert "authorization" not in forwarded["headers"]


def test_nim_chat_adds_bearer_header_and_translates_model(monkeypatch):
    monkeypatch.setenv("NIM_API_KEY", "nim-test-key")
    monkeypatch.setattr(
        gateway_router,
        "CHAT_MODEL_ROUTES",
        {
            "fincontext-planner": BackendRoute(
                model_name="fincontext-planner",
                upstream_base_url="https://integrate.api.nvidia.com/v1",
                upstream_path="/chat/completions",
                upstream_model_name="Qwen/Qwen2.5-14B-Instruct",
            )
        },
    )
    captured: list[dict[str, object]] = []
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_capture_transport(captured))
        response = client.post(
            "/v1/chat/completions",
            json={"model": "fincontext-planner", "messages": [{"role": "user", "content": "plan"}]},
        )
        assert response.status_code == 200

    forwarded = captured[0]
    assert forwarded["path"] == "/v1/chat/completions"
    assert forwarded["headers"]["authorization"] == "Bearer nim-test-key"
    assert forwarded["json"]["model"] == "Qwen/Qwen2.5-14B-Instruct"


def test_embedding_route_does_not_receive_nim_auth(monkeypatch):
    monkeypatch.setenv("NIM_API_KEY", "nim-test-key")
    captured: list[dict[str, object]] = []
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_capture_transport(captured))
        response = client.post("/v1/embeddings", json={"input": ["alpha"]})
        assert response.status_code == 200

    forwarded = captured[0]
    assert forwarded["path"] == "/v1/embeddings"
    assert "authorization" not in forwarded["headers"]


def test_embeddings_proxy_returns_payload():
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_transport())
        response = client.post("/v1/embeddings", json={"input": ["alpha"]})
        assert response.status_code == 200
        assert response.json()["data"][0]["embedding"] == [0.1, 0.2, 0.3]


def test_health_reports_services():
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_transport())
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert len(response.json()["services"]) == 4


def test_metrics_accumulate_requests():
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_transport())
        client.post("/v1/chat/completions", json={"model": "fincontext-planner", "messages": [{"role": "user", "content": "plan"}]})
        response = client.get("/metrics")
        payload = response.json()
        assert response.status_code == 200
        assert payload["recent_requests"] >= 1
        assert "fincontext-planner" in payload["models"]
