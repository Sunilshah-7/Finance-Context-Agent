from __future__ import annotations

import os

from fastapi import HTTPException, status

from models import BackendRoute


CHAT_MODEL_ROUTES = {
    "fincontext-reasoner": BackendRoute(
        model_name="fincontext-reasoner",
        upstream_base_url=os.getenv("VLLM_REASONER_URL", "http://localhost:8000/v1"),
        upstream_path="/chat/completions",
    ),
    "fincontext-planner": BackendRoute(
        model_name="fincontext-planner",
        upstream_base_url=os.getenv("VLLM_PLANNER_URL", "http://localhost:8001/v1"),
        upstream_path="/chat/completions",
    ),
}

EMBEDDING_ROUTE = BackendRoute(
    model_name="fincontext-embedding",
    upstream_base_url=os.getenv("EMBEDDING_URL", "http://localhost:8002"),
    upstream_path="/v1/embeddings",
)

RERANK_ROUTE = BackendRoute(
    model_name="fincontext-reranker",
    upstream_base_url=os.getenv("RERANKER_URL", "http://localhost:8003"),
    upstream_path="/v1/rerank",
)


def route_chat_model(model_name: str) -> BackendRoute:
    route = CHAT_MODEL_ROUTES.get(model_name)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "unsupported_model",
                    "message": f"Unsupported model '{model_name}'.",
                    "retryable": False,
                    "request_id": "unknown",
                }
            },
        )
    return route


def embedding_route() -> BackendRoute:
    return EMBEDDING_ROUTE


def rerank_route() -> BackendRoute:
    return RERANK_ROUTE
