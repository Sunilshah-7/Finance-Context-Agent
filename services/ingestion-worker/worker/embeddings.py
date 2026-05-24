"""Embedding client for the Inference Gateway.

Ingestion never calls TEI directly. This client batches text and sends
OpenAI-style ``/v1/embeddings`` requests to the Gateway, then validates that
BGE-large vectors have the expected 1024 dimensions before Qdrant upsert.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

import httpx

DEFAULT_BATCH_SIZE = 256
DEFAULT_MODEL = "fincontext-embedding"
EXPECTED_DIMENSIONS = 1024


class EmbeddingClient:
    def __init__(
        self,
        gateway_url: str,
        *,
        model: str = DEFAULT_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        expected_dimensions: int = EXPECTED_DIMENSIONS,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.gateway_url = gateway_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.expected_dimensions = expected_dimensions
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=60.0)

    async def __aenter__(self) -> EmbeddingClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in _batches(texts, self.batch_size):
            vectors.extend(await self._embed_batch(batch))
        return vectors

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = {"input": texts, "model": self.model}
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = await self._client.post(
                    f"{self.gateway_url}/v1/embeddings", json=payload
                )
                response.raise_for_status()
                vectors = _parse_embedding_response(response.json())
                self._validate_vectors(vectors, expected_count=len(texts))
                return vectors
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                await asyncio.sleep(0.5 * (2**attempt))

        raise RuntimeError(f"embedding request failed after retries: {last_error}")

    def _validate_vectors(
        self, vectors: list[list[float]], *, expected_count: int
    ) -> None:
        if len(vectors) != expected_count:
            raise ValueError(
                f"expected {expected_count} embeddings, received {len(vectors)}"
            )
        for index, vector in enumerate(vectors):
            if len(vector) != self.expected_dimensions:
                raise ValueError(
                    f"embedding {index} has {len(vector)} dimensions; "
                    f"expected {self.expected_dimensions}"
                )


async def embed_batch(texts: list[str], gateway_url: str) -> list[list[float]]:
    async with EmbeddingClient(gateway_url) as client:
        return await client.embed_texts(texts)


def _parse_embedding_response(payload: dict) -> list[list[float]]:
    data = payload["data"]
    ordered = sorted(data, key=lambda item: item.get("index", 0))
    return [list(item["embedding"]) for item in ordered]


def _batches(values: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]
