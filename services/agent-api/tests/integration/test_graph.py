"""Integration test for the analysis graph fallback execution path.

This test verifies that running the graph on an empty or missing portfolio still
returns a partial analysis state and produces a memo through the direct graph
runner.
"""

from __future__ import annotations

from fincontext_schemas import AnalysisState

from app.graph import run_analysis_graph

pytestmark = __import__("pytest").mark.asyncio


async def test_graph_returns_state_for_empty_portfolio() -> None:
    result = await run_analysis_graph(AnalysisState(user_id="u", portfolio_id="missing"))
    assert result.partial is True
    assert result.memo is not None
