"""Retrieve evidence chunks for the current analysis plan.

This node checks that a retrieval plan exists, runs the hybrid retrieval
pipeline for that plan, and writes the resulting evidence chunks to
`AnalysisState.retrieved_chunks`. If retrieval cannot run or fails, it records
an error in state and marks the analysis as partial.
"""

from __future__ import annotations

from fincontext_schemas import AnalysisState

from app.retrieval import hybrid_retrieve


async def filing_retrieval(state: AnalysisState) -> AnalysisState:
    if state.retrieval_plan is None:
        return state.model_copy(
            update={
                "error": state.error or "filing_retrieval skipped: missing retrieval_plan",
                "partial": True,
            }
        )
    try:
        chunks = await hybrid_retrieve(state.retrieval_plan)
        return state.model_copy(update={"retrieved_chunks": chunks})
    except Exception as exc:  # noqa: BLE001 - node errors should be captured in state
        return state.model_copy(update={"error": f"filing_retrieval failed: {exc}", "partial": True})
