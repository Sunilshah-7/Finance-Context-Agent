from __future__ import annotations

from datetime import date, timedelta
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

import httpx
from pydantic import ValidationError

try:
    from fincontext_schemas import AnalysisState, Holding, RetrievalPlan
except ModuleNotFoundError:  # local Python may not have the editable package installed
    schema_src = Path(__file__).resolve().parents[4] / "packages" / "schemas" / "python"
    sys.path.insert(0, str(schema_src))
    from state import AnalysisState, Holding, RetrievalPlan  # type: ignore[no-redef]


logger = logging.getLogger(__name__)

DEFAULT_GATEWAY_URL = "http://localhost:8080"
DEFAULT_FILING_TYPES = ["10-K", "10-Q"]
DEFAULT_SECTIONS = ["Item 1A", "Item 7"]
DEFAULT_LOOKBACK_YEARS = 3
DEFAULT_BM25_KEYWORDS = [
    "risk factors",
    "material disclosures",
    "management discussion",
    "liquidity",
    "competition",
    "supply chain",
    "customer concentration",
    "guidance",
]

PLANNER_SYSTEM_PROMPT = """You are a financial analyst planning SEC filing research queries.

You will receive a portfolio and an optional user question. Produce one strict JSON object matching this exact schema:
{
  "query": "string",
  "target_tickers": ["string"],
  "filing_types": ["string"],
  "sections": ["string"],
  "date_range_start": "YYYY-MM-DD",
  "date_range_end": "YYYY-MM-DD",
  "bm25_keywords": ["string"]
}

Requirements:
- Focus on material risks and recent disclosures relevant to each holding.
- Treat the portfolio tickers as the full allowed ticker universe. Do not invent new tickers.
- Use filing_types appropriate for SEC disclosure review, typically 10-K and 10-Q.
- Prioritize sections that surface risks and operating changes, especially Item 1A and Item 7.
- The query field must be a single natural-language retrieval query that can be reused with ticker filters downstream.
- Include concise bm25_keywords that improve keyword matching for the portfolio themes.
- Do not provide buy, sell, hold, or short recommendations.
- Return JSON only. No markdown, no commentary."""


def _resolve_gateway_url() -> str:
    return os.getenv("INFERENCE_GATEWAY_URL", DEFAULT_GATEWAY_URL)


def _sorted_holdings(holdings: list[Holding]) -> list[Holding]:
    return sorted(holdings, key=lambda holding: holding.weight, reverse=True)


def _portfolio_summary(holdings: list[Holding]) -> list[dict[str, Any]]:
    return [
        {
            "ticker": holding.ticker,
            "name": holding.name,
            "weight": holding.weight,
            "sector": holding.sector,
            "shares": holding.shares,
            "avg_cost": holding.avg_cost,
        }
        for holding in _sorted_holdings(holdings)
    ]


def _build_user_message(state: AnalysisState) -> str:
    payload = {
        "question": state.question or "general portfolio review",
        "today": date.today().isoformat(),
        "holdings": _portfolio_summary(state.holdings),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _default_date_range() -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=365 * DEFAULT_LOOKBACK_YEARS)
    return start.isoformat(), end.isoformat()


def _keywordize(text: str) -> list[str]:
    words = [word.strip(" ,.;:()[]{}").lower() for word in text.split()]
    keywords: list[str] = []
    for word in words:
        if len(word) < 4 or not word:
            continue
        if word not in keywords:
            keywords.append(word)
    return keywords


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _build_fallback_query(holdings: list[Holding], question: str | None) -> str:
    tickers = ", ".join(holding.ticker for holding in _sorted_holdings(holdings))
    if question:
        return (
            f"For portfolio holdings {tickers}, find risk factors and material disclosures "
            f"most relevant to this question: {question}"
        )
    return (
        f"For portfolio holdings {tickers}, find risk factors, management discussion changes, "
        "and material disclosures."
    )


def _build_fallback_keywords(holdings: list[Holding], question: str | None) -> list[str]:
    holding_keywords: list[str] = []
    for holding in _sorted_holdings(holdings):
        holding_keywords.extend(
            [
                holding.ticker,
                holding.sector,
                f"{holding.ticker} risk factors",
                f"{holding.ticker} material disclosures",
            ]
        )

    question_keywords = _keywordize(question or "")
    return _dedupe_keep_order(
        [
            *holding_keywords,
            *question_keywords,
            *DEFAULT_BM25_KEYWORDS,
        ]
    )


def _fallback_plan(state: AnalysisState) -> RetrievalPlan:
    date_range_start, date_range_end = _default_date_range()
    sorted_holdings = _sorted_holdings(state.holdings)
    return RetrievalPlan(
        query=_build_fallback_query(sorted_holdings, state.question),
        target_tickers=[holding.ticker for holding in sorted_holdings],
        filing_types=list(DEFAULT_FILING_TYPES),
        sections=list(DEFAULT_SECTIONS),
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        bm25_keywords=_build_fallback_keywords(sorted_holdings, state.question),
    )


async def _fetch_plan_from_gateway(state: AnalysisState, gateway_url: str) -> RetrievalPlan:
    # TODO: replace with gateway client when services/agent-api/app/clients/gateway.py is available
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{gateway_url.rstrip('/')}/v1/chat/completions",
            json={
                "model": "fincontext-planner",
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_message(state)},
                ],
            },
        )

    if response.status_code != 200:
        raise RuntimeError(f"Inference Gateway returned HTTP {response.status_code}: {response.text}")

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    plan = RetrievalPlan.model_validate(parsed)

    allowed_tickers = {holding.ticker for holding in state.holdings}
    invalid_tickers = [ticker for ticker in plan.target_tickers if ticker not in allowed_tickers]
    if invalid_tickers:
        raise ValueError(f"Planner response included unknown tickers: {', '.join(invalid_tickers)}")

    return plan


async def portfolio_context_planner(state: AnalysisState) -> AnalysisState:
    """
    Reads the portfolio from state, calls Qwen2.5-14B via the Inference
    Gateway to generate a RetrievalPlan, and returns the updated state
    with the plan attached.

    Falls back to a deterministic plan if the LLM call fails or returns
    malformed output.
    """
    if not state.holdings:
        empty_plan = _fallback_plan(state)
        return state.model_copy(
            update={
                "target_tickers": empty_plan.target_tickers,
                "retrieval_plan": empty_plan,
            }
        )

    gateway_url = _resolve_gateway_url()
    try:
        plan = await _fetch_plan_from_gateway(state, gateway_url)
    except (httpx.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValidationError, ValueError, RuntimeError) as exc:
        logger.warning("portfolio_context_planner falling back to deterministic plan: %s", exc)
        plan = _fallback_plan(state)

    return state.model_copy(
        update={
            "target_tickers": plan.target_tickers,
            "retrieval_plan": plan,
        }
    )
