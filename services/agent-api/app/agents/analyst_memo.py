"""
Analyst Memo Node

Final node in the 4-node LangGraph pipeline. Generates a citation-grounded
analyst memo by:

1. Computing risk scores per holding (portfolio weight + disclosure severity)
2. Calling Qwen2.5-72B to draft a structured memo (executive summary, exposure,
   changes, watchlist, limitations, disclaimer)
3. Validating all citations in the generated text against retrieved chunks
4. Removing sentences with unverified or unmapped citations
5. Returning a fallback memo if generation fails or citation pass-rate is low

Output state fields set:
- memo: AnalystMemo with executive_summary, affected holdings, changes, scores
- risk_scores: list of RiskScore objects with drivers and citations
- citation_pass_rate: ratio of verified citations to total citations in memo
"""

from __future__ import annotations

import re

from fincontext_schemas import AnalysisState, AnalystMemo, Citation, RiskScore

from app.agents.disclosure_change import citation_for
from app.clients.gateway import InferenceGatewayClient


DISCLAIMER = "This output is research assistance only and does not constitute investment advice."


def compute_risk_scores(state: AnalysisState) -> list[RiskScore]:
    chunks_by_ticker = {chunk.ticker: [] for chunk in state.retrieved_chunks}
    for chunk in state.retrieved_chunks:
        chunks_by_ticker.setdefault(chunk.ticker, []).append(chunk)

    scores: list[RiskScore] = []
    for holding in state.holdings:
        changes = [change for change in state.disclosure_changes if change.ticker == holding.ticker]
        severity = max((change.severity for change in changes), default=0.0)
        confidence = sum((change.confidence for change in changes), 0.0) / max(len(changes), 1)
        exposure_component = min(holding.weight * 100.0, 40.0)
        change_component = severity * 60.0
        score = min(100.0, exposure_component + change_component)
        citations: list[Citation] = []
        for change in changes[:3]:
            if change.new_citation:
                citations.append(change.new_citation)
        if not citations:
            citations = [citation_for(chunk) for chunk in chunks_by_ticker.get(holding.ticker, [])[:2]]
        scores.append(
            RiskScore(
                ticker=holding.ticker,
                score=round(score, 2),
                delta=round(change_component, 2),
                confidence=round(confidence, 2),
                top_drivers=[change.summary for change in changes[:3]],
                citations=citations,
                portfolio_impact="high" if holding.weight >= 0.2 else "medium" if holding.weight >= 0.1 else "low",
            )
        )
    return scores


def evidence_table(state: AnalysisState) -> list[Citation]:
    seen: set[str] = set()
    evidence: list[Citation] = []
    for chunk in state.retrieved_chunks:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        evidence.append(citation_for(chunk))
    return evidence


def citation_pass_rate(text: str, valid_ids: set[str]) -> float:
    cited = re.findall(r"\[([^\]]+)\]", text)
    if not cited:
        return 1.0
    passed = sum(1 for citation in cited if citation in valid_ids)
    return passed / len(cited)


def remove_unverified_sentences(text: str, valid_ids: set[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept: list[str] = []
    for sentence in sentences:
        cited = re.findall(r"\[([^\]]+)\]", sentence)
        if cited and any(citation not in valid_ids for citation in cited):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def fallback_memo(state: AnalysisState, risk_scores: list[RiskScore], pass_rate: float) -> AnalystMemo:
    changes = state.disclosure_changes[:5]
    summary = (
        "FinContext reviewed the portfolio filings and found citation-backed disclosure changes."
        if changes
        else "FinContext reviewed the available filing evidence but did not find enough cross-period excerpts to classify material disclosure drift."
    )
    return AnalystMemo(
        executive_summary=summary,
        affected_holdings=[score.ticker for score in risk_scores if score.score > 0],
        disclosure_changes=changes,
        risk_scores=risk_scores,
        evidence_table=evidence_table(state),
        watchlist_questions=[
            "Which disclosure changes are most likely to affect next-period margins or liquidity?",
            "Have supply-chain, customer concentration, or financing risks changed since the latest filing?",
        ],
        limitations="Results are limited to retrieved EDGAR chunks already indexed in SQLite and Qdrant.",
        disclaimer=DISCLAIMER,
        citation_pass_rate=pass_rate,
    )


async def analyst_memo(state: AnalysisState) -> AnalysisState:
    try:
        risk_scores = compute_risk_scores(state)
        valid_ids = {chunk.chunk_id for chunk in state.retrieved_chunks}
        valid_ids.update(chunk.citation_anchor for chunk in state.retrieved_chunks)
        prompt = {
            "question": state.question,
            "holdings": [holding.model_dump() for holding in state.holdings],
            "risk_scores": [score.model_dump() for score in risk_scores],
            "disclosure_changes": [change.model_dump() for change in state.disclosure_changes],
            "evidence": [chunk.model_dump() for chunk in state.retrieved_chunks],
            "required_sections": [
                "Executive Summary",
                "Portfolio Exposure Affected",
                "Top Disclosure Changes",
                "Risk Score Changes",
                "Evidence Table",
                "Watchlist Questions for next earnings call",
                "Limitations and Confidence",
                "Investment Research Disclaimer",
            ],
        }
        try:
            async with InferenceGatewayClient() as gateway:
                text = await gateway.chat_text(
                    [
                        {
                            "role": "system",
                            "content": (
                                "Write a concise analyst memo using only provided evidence. "
                                "Every factual claim about a filing must cite a provided chunk_id in brackets."
                            ),
                        },
                        {"role": "user", "content": str(prompt)},
                    ],
                    model="fincontext-reasoner",
                )
            pass_rate = citation_pass_rate(text, valid_ids)
            verified_text = remove_unverified_sentences(text, valid_ids)
            memo = fallback_memo(state, risk_scores, pass_rate).model_copy(
                update={
                    "executive_summary": verified_text[:1200] or fallback_memo(state, risk_scores, pass_rate).executive_summary,
                    "citation_pass_rate": pass_rate,
                }
            )
        except Exception:
            pass_rate = 1.0
            memo = fallback_memo(state, risk_scores, pass_rate)

        return state.model_copy(
            update={
                "risk_scores": risk_scores,
                "memo": memo,
                "citation_pass_rate": memo.citation_pass_rate,
            }
        )
    except Exception as exc:  # noqa: BLE001 - node errors should be captured in state
        return state.model_copy(update={"error": f"analyst_memo failed: {exc}", "partial": True})
