from __future__ import annotations

from pathlib import Path
import sys

import httpx
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main import app  # noqa: E402


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


def test_chat_proxy_routes_to_reasoner():
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_transport())
        response = client.post(
            "/v1/chat/completions",
            json={"model": "fincontext-reasoner", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "ok"


def test_embeddings_proxy_returns_payload():
    with TestClient(app) as client:
        client.app.state.http = httpx.AsyncClient(transport=make_transport())
        response = client.post("/v1/embeddings", json={"input": ["alpha"]})
        assert response.status_code == 200
        assert response.json()["data"][0]["embedding"] == [0.1, 0.2, 0.3]


def test_health_reports_services(monkeypatch):
    monkeypatch.setenv("NIM_API_KEY", "test-key")
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
