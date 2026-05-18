from __future__ import annotations

import time
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from metrics import RollingMetricsStore
from middleware import RequestContextMiddleware
from models import HealthCheckResult, RequestMetric
from router import CHAT_MODEL_ROUTES, embedding_route, rerank_route, route_chat_model


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    app.state.metrics = RollingMetricsStore(capacity=1000)
    yield
    await app.state.http.aclose()


app = FastAPI(title="FinContext Inference Gateway", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)


def _error_response(request_id: str, code: str, message: str, retryable: bool, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "request_id": request_id,
            }
        },
    )


def _usage_metrics(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = payload.get("usage") or {}
    return usage.get("prompt_tokens"), usage.get("completion_tokens")


def _upstream_headers(request: Request, route_model: str | None = None) -> dict[str, str]:
    headers = {"x-request-id": request.state.request_id}
    if route_model in {"fincontext-reasoner", "fincontext-planner"}:
        nim_api_key = os.getenv("NIM_API_KEY")
        if nim_api_key:
            headers["Authorization"] = f"Bearer {nim_api_key}"
    return headers


async def _proxy_json(
    request: Request,
    route_url: str,
    payload: dict[str, Any],
    endpoint: str,
    metric_model: str,
) -> JSONResponse:
    try:
        response = await request.app.state.http.post(route_url, json=payload, headers=_upstream_headers(request, metric_model))
    except httpx.HTTPError as exc:
        logger.warning("upstream_request_failed", request_id=request.state.request_id, endpoint=endpoint, error=str(exc))
        return _error_response(request.state.request_id, "upstream_unavailable", str(exc), True, 502)

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return JSONResponse(status_code=response.status_code, content={"detail": response.text})

    data = response.json()
    input_tokens, output_tokens = _usage_metrics(data)
    latency_ms = round((time.perf_counter() - request.state.started_at) * 1000, 3)
    tokens_per_second = None
    if output_tokens and latency_ms > 0:
        tokens_per_second = round(output_tokens / (latency_ms / 1000), 3)
    request.app.state.metrics.record(
        RequestMetric(
            endpoint=endpoint,
            model=metric_model,
            status_code=response.status_code,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens_per_second=tokens_per_second,
        )
    )
    return JSONResponse(status_code=response.status_code, content=data)


async def _stream_proxy(
    request: Request,
    route_url: str,
    payload: dict[str, Any],
    endpoint: str,
    metric_model: str,
) -> StreamingResponse:
    async def iterator() -> AsyncIterator[bytes]:
        first_chunk_ms: float | None = None
        output_tokens = 0
        async with request.app.state.http.stream(
            "POST",
            route_url,
            json=payload,
            headers=_upstream_headers(request, metric_model),
        ) as upstream:
            if upstream.status_code >= 400:
                body = await upstream.aread()
                yield body
                return

            async for chunk in upstream.aiter_bytes():
                if chunk and first_chunk_ms is None:
                    first_chunk_ms = round((time.perf_counter() - request.state.started_at) * 1000, 3)
                if chunk:
                    output_tokens += max(chunk.count(b"data:"), 0)
                yield chunk

        latency_ms = round((time.perf_counter() - request.state.started_at) * 1000, 3)
        tokens_per_second = None
        if output_tokens and latency_ms > 0:
            tokens_per_second = round(output_tokens / (latency_ms / 1000), 3)
        request.app.state.metrics.record(
            RequestMetric(
                endpoint=endpoint,
                model=metric_model,
                status_code=200,
                latency_ms=latency_ms,
                input_tokens=None,
                output_tokens=output_tokens or None,
                time_to_first_token_ms=first_chunk_ms,
                tokens_per_second=tokens_per_second,
            )
        )

    return StreamingResponse(iterator(), media_type="text/event-stream")


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    checks: list[HealthCheckResult] = []
    services = {
        "reasoner": CHAT_MODEL_ROUTES["fincontext-reasoner"].upstream_base_url,
        "planner": CHAT_MODEL_ROUTES["fincontext-planner"].upstream_base_url,
        "embedding": embedding_route().upstream_base_url,
        "reranker": rerank_route().upstream_base_url,
    }
    for name, base_url in services.items():
        url = f"{base_url.rstrip('/')}/health"
        if name in {"reasoner", "planner"} and base_url.startswith("https://integrate.api.nvidia.com"):
            status = "ready" if os.getenv("NIM_API_KEY") else "error"
            detail = None if status == "ready" else "NIM_API_KEY is not set"
            checks.append(HealthCheckResult(name=name, status=status, url=base_url, detail=detail))
            continue
        try:
            response = await request.app.state.http.get(url)
            status = "ready" if response.is_success else "error"
            detail = None if response.is_success else response.text[:200]
        except httpx.HTTPError as exc:
            status = "error"
            detail = str(exc)
        checks.append(HealthCheckResult(name=name, status=status, url=url, detail=detail))

    overall = "ok" if all(check.status == "ready" for check in checks) else "degraded"
    return {
        "status": overall,
        "services": [check.model_dump() for check in checks],
    }


@app.get("/metrics")
async def metrics(request: Request) -> dict[str, Any]:
    return request.app.state.metrics.summary().model_dump()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    model_name = payload.get("model")
    if not model_name:
        return _error_response(request.state.request_id, "missing_model", "Request body must include 'model'.", False, 400)

    try:
        route = route_chat_model(model_name)
    except HTTPException as exc:
        detail = exc.detail["error"]
        detail["request_id"] = request.state.request_id
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    upstream_payload = dict(payload)
    if route.upstream_model_name:
        upstream_payload["model"] = route.upstream_model_name

    if payload.get("stream") is True:
        return await _stream_proxy(request, route.url, upstream_payload, "/v1/chat/completions", model_name)
    return await _proxy_json(request, route.url, upstream_payload, "/v1/chat/completions", model_name)


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    payload = await request.json()
    payload.setdefault("model", embedding_route().model_name)
    return await _proxy_json(request, embedding_route().url, payload, "/v1/embeddings", embedding_route().model_name)


@app.post("/v1/rerank")
async def rerank(request: Request):
    payload = await request.json()
    return await _proxy_json(request, rerank_route().url, payload, "/v1/rerank", rerank_route().model_name)
