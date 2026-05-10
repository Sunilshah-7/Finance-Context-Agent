"""Compare retrieved SEC filing chunks and classify disclosure language changes.

This node groups retrieved chunks by ticker, section, and filing type, compares
the earliest and latest filings for each group, and uses the inference gateway
with a heuristic fallback to classify whether the language represents a new,
removed, intensified, softened, metric, or accounting-related disclosure change.
The resulting non-boilerplate changes are written back to `AnalysisState` as
`disclosure_changes`.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fincontext_schemas import AnalysisState, Citation, DisclosureChange

from app.clients.gateway import InferenceGatewayClient


VALID_CHANGE_TYPES = {
    "new_risk",
    "removed_risk",
    "intensified_language",
    "softened_language",
    "metric_changed",
    "legal_accounting_update",
}


def citation_for(chunk: Any) -> Citation:
    return Citation(
        chunk_id=chunk.chunk_id,
        citation_anchor=chunk.citation_anchor,
        source_url=chunk.source_url,
        filed_at=chunk.filed_at,
        ticker=chunk.ticker,
        filing_type=chunk.filing_type,
        section=chunk.section,
    )


def heuristic_change(old_text: str, new_text: str) -> tuple[str, str, float, float]:
    risk_words = ("material", "adverse", "significant", "substantial", "uncertain", "depends", "concentration")
    old_hits = sum(word in old_text.lower() for word in risk_words)
    new_hits = sum(word in new_text.lower() for word in risk_words)
    if new_hits > old_hits:
        return ("intensified_language", "Risk-bearing language appears stronger in the newer filing.", 0.65, 0.45)
    if new_hits < old_hits:
        return ("softened_language", "Risk-bearing language appears softer in the newer filing.", 0.4, 0.4)
    return ("new_risk", "The retrieved filing language changed across periods and needs analyst review.", 0.5, 0.35)


async def classify_pair(old_chunk: Any, new_chunk: Any) -> DisclosureChange | None:
    old_text = old_chunk.text[:4000]
    new_text = new_chunk.text[:4000]
    try:
        async with InferenceGatewayClient() as gateway:
            data = await gateway.chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "Compare two SEC filing excerpts. Return JSON with change_type, "
                            "summary, severity, confidence. change_type must be one of "
                            "new_risk, removed_risk, intensified_language, softened_language, "
                            "metric_changed, legal_accounting_update, boilerplate."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Ticker: {new_chunk.ticker}\nSection: {new_chunk.section}\n"
                            f"Old filing {old_chunk.filed_at}:\n{old_text}\n\n"
                            f"New filing {new_chunk.filed_at}:\n{new_text}"
                        ),
                    },
                ],
                model="fincontext-planner",
            )
        change_type = str(data.get("change_type", "boilerplate"))
        if change_type == "boilerplate" or change_type not in VALID_CHANGE_TYPES:
            return None
        summary = str(data.get("summary", "Disclosure language changed."))
        severity = float(data.get("severity", 0.5))
        confidence = float(data.get("confidence", 0.5))
    except Exception:
        change_type, summary, severity, confidence = heuristic_change(old_text, new_text)

    return DisclosureChange(
        ticker=new_chunk.ticker,
        section=new_chunk.section,
        change_type=change_type,  # type: ignore[arg-type]
        old_citation=citation_for(old_chunk),
        new_citation=citation_for(new_chunk),
        summary=summary,
        severity=max(0.0, min(1.0, severity)),
        confidence=max(0.0, min(1.0, confidence)),
    )


async def disclosure_change(state: AnalysisState) -> AnalysisState:
    try:
        groups: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
        for chunk in state.retrieved_chunks:
            groups[(chunk.ticker, chunk.section, chunk.filing_type)].append(chunk)

        pairs: list[tuple[Any, Any]] = []
        for chunks in groups.values():
            by_date: dict[str, list[Any]] = defaultdict(list)
            for chunk in chunks:
                by_date[chunk.filed_at].append(chunk)
            dates = sorted(by_date)
            if len(dates) < 2:
                continue
            old = sorted(by_date[dates[0]], key=lambda item: item.chunk_index)[0]
            new = sorted(by_date[dates[-1]], key=lambda item: item.chunk_index)[0]
            if old.text.strip() != new.text.strip():
                pairs.append((old, new))

        changes = await asyncio.gather(*(classify_pair(old, new) for old, new in pairs))
        return state.model_copy(update={"disclosure_changes": [change for change in changes if change is not None]})
    except Exception as exc:  # noqa: BLE001 - node errors should be captured in state
        return state.model_copy(update={"error": f"disclosure_change failed: {exc}", "partial": True})
