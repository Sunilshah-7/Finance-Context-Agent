"""Tests for the agent nodes that transform retrieval results into analysis output.

These tests cover the disclosure change heuristic path and the analyst memo
fallback path to ensure the node logic produces changes, a memo, and citation
metadata even when the gateway response is not available.
"""

from __future__ import annotations

from fincontext_schemas import AnalysisState, EvidenceChunk

from app.agents.analyst_memo import DISCLAIMER, analyst_memo
from app.agents.disclosure_change import disclosure_change

pytestmark = __import__("pytest").mark.asyncio


def sample_chunk(chunk_id: str, filed_at: str, text: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        document_id="doc",
        ticker="AMD",
        filing_type="10-K",
        filed_at=filed_at,
        section="Item 1A",
        item_label="Risk Factors",
        text=text,
        citation_anchor=f"AMD 10-K Item 1A paragraph {chunk_id}",
        source_url="https://sec.gov/example",
        chunk_index=0,
        rerank_score=1.0,
    )


async def test_disclosure_change_heuristic() -> None:
    state = AnalysisState(
        user_id="u",
        portfolio_id="p",
        retrieved_chunks=[
            sample_chunk("old", "2023-01-01", "We may depend on suppliers."),
            sample_chunk("new", "2025-01-01", "We significantly depend on suppliers and material shortages may adversely affect us."),
        ],
    )
    result = await disclosure_change(state)
    assert result.disclosure_changes


async def test_analyst_memo_fallback() -> None:
    state = AnalysisState(
        user_id="u",
        portfolio_id="p",
        retrieved_chunks=[sample_chunk("c1", "2025-01-01", "Risk text.")],
    )
    result = await analyst_memo(state)
    assert result.memo is not None
    assert result.citation_pass_rate is not None
    assert result.memo.disclaimer == DISCLAIMER
    assert DISCLAIMER == "This output is research assistance only and does not constitute investment advice."
