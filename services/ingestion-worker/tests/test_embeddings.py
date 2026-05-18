"""Embedding client tests using mocked Gateway responses."""

from __future__ import annotations

import asyncio

import httpx

from worker.embeddings import EmbeddingClient


def test_embedding_client_parses_openai_style_response():
    async def run_test() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            embedding_client = EmbeddingClient(
                "http://gateway.local",
                http_client=client,
            )
            vectors = await embedding_client.embed_texts(["alpha", "beta"])

        assert len(vectors) == 2
        assert len(vectors[0]) == 1024
        assert vectors[1][0] == 0.2

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        payload = request.read()
        assert b"fincontext-embedding" in payload
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [0.1] * 1024},
                    {"index": 1, "embedding": [0.2] * 1024},
                ]
            },
        )

    asyncio.run(run_test())
