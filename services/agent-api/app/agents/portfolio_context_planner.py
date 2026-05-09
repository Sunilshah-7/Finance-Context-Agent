from __future__ import annotations

import asyncio
from datetime import date

from fincontext_schemas import AnalysisState, RetrievalPlan

from app.clients.db import SQLiteClient
from app.clients.gateway import InferenceGatewayClient


def default_plan(state: AnalysisState) -> RetrievalPlan:
    tickers = state.target_tickers or [holding.ticker for holding in state.holdings[:5]]
    question = state.question or "Review disclosure changes and portfolio risk."
    return RetrievalPlan(
        query=question,
        target_tickers=tickers,
        filing_types=["10-K", "10-Q"],
        sections=["Item 1", "Item 1A", "Item 7", "Item 7A", "item_1", "item_1a", "item_7", "item_7a"],
        date_range_start=f"{date.today().year - 4}-01-01",
        date_range_end=date.today().isoformat(),
        bm25_keywords=[
            "risk",
            "supply chain",
            "customer concentration",
            "liquidity",
            "materially adversely",
        ],
    )


async def portfolio_context_planner(state: AnalysisState) -> AnalysisState:
    try:
        db = SQLiteClient()
        holdings = await asyncio.to_thread(db.load_holdings, state.portfolio_id)
        target_tickers = [holding.ticker for holding in sorted(holdings, key=lambda item: item.weight, reverse=True)[:5]]
        planned_state = state.model_copy(update={"holdings": holdings, "target_tickers": target_tickers})
        fallback = default_plan(planned_state)

        if not holdings:
            return planned_state.model_copy(
                update={
                    "retrieval_plan": fallback,
                    "partial": True,
                    "error": "No holdings found for portfolio.",
                }
            )

        prompt = {
            "holdings": [holding.model_dump() for holding in holdings],
            "question": state.question,
            "default_filing_types": fallback.filing_types,
            "default_sections": ["Item 1A", "Item 7", "Item 7A"],
        }
        try:
            async with InferenceGatewayClient() as gateway:
                data = await gateway.chat_json(
                    [
                        {
                            "role": "system",
                            "content": (
                                "You are a financial retrieval planner. Return JSON with keys: "
                                "query, target_tickers, filing_types, sections, date_range_start, "
                                "date_range_end, bm25_keywords. Prioritize the largest holdings."
                            ),
                        },
                        {"role": "user", "content": str(prompt)},
                    ],
                    model="fincontext-planner",
                )
            plan = RetrievalPlan.model_validate({**fallback.model_dump(), **data})
            if not plan.target_tickers:
                plan = plan.model_copy(update={"target_tickers": target_tickers})
        except Exception:
            plan = fallback

        return planned_state.model_copy(update={"retrieval_plan": plan})
    except Exception as exc:  # noqa: BLE001 - node errors should be captured in state
        return state.model_copy(update={"error": f"portfolio_context_planner failed: {exc}", "partial": True})
