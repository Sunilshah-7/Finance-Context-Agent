from __future__ import annotations

import os

from fastapi import HTTPException, status

from models import BackendRoute


# Kishan-owned routing table for the gateway foundation.
# Sunil's infra setup must provide matching env vars/services; Abhiyan and the Agent API
# side should treat these model names as the stable entrypoints to call.
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
    # Resolves the logical model name used by the Agent API into a concrete upstream.
    # If the team later renames planner/reasoner models, this function likely needs
    # a code update here rather than just external input.
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
    # Shared by ingestion and retrieval flows; upstream URL should come from infra config.
    return EMBEDDING_ROUTE


def rerank_route() -> BackendRoute:
    # Shared by retrieval flows once filing_retrieval is wired into Agent API.
    return RERANK_ROUTE
