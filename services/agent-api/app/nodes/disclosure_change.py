"""
This is the disclosure_change LangGraph node.
It compares chunks from current and prior filings to identify material changes.
The current implementation uses placeholder similarity and classification logic.
See TODOs for the real Qwen-14B integration.
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from datetime import date

from packages.schemas.python.state import (
    AnalysisState,
    ChangeType,
    Citation,
    DisclosureChange,
    EvidenceChunk,
)

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.6
MAX_PAIRS_PER_GROUP = 10
CLASSIFIER_MODEL = "fincontext-planner"
INFERENCE_GATEWAY_URL = os.getenv("INFERENCE_GATEWAY_URL", "http://localhost:8080")

DISCLOSURE_SYSTEM_PROMPT = (
    "You compare disclosure text between filings and identify material changes. "
    "Return a structured classification with citations."
)


def group_chunks_by_ticker_section(
    chunks: list[EvidenceChunk],
) -> dict[tuple[str, str], list[EvidenceChunk]]:
    """Group retrieved chunks by (ticker, section) for downstream comparison."""
    grouped: dict[tuple[str, str], list[EvidenceChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[(chunk.ticker, chunk.section)].append(chunk)
    return dict(grouped)


def split_current_vs_prior(
    chunks: list[EvidenceChunk],
) -> tuple[list[EvidenceChunk], list[EvidenceChunk]]:
    """Split a group into the most recent filing's chunks and the next-most-recent filing's chunks."""
    if not chunks:
        return [], []

    sorted_chunks = sorted(chunks, key=lambda chunk: _parse_filed_at(chunk.filed_at), reverse=True)
    distinct_dates: list[str] = []
    for chunk in sorted_chunks:
        if chunk.filed_at not in distinct_dates:
            distinct_dates.append(chunk.filed_at)
        if len(distinct_dates) == 2:
            break

    current_date = distinct_dates[0]
    current_chunks = [chunk for chunk in sorted_chunks if chunk.filed_at == current_date]

    if len(distinct_dates) == 1:
        return current_chunks, []

    prior_date = distinct_dates[1]
    prior_chunks = [chunk for chunk in sorted_chunks if chunk.filed_at == prior_date]
    return current_chunks, prior_chunks


def find_chunk_pairs(
    current: list[EvidenceChunk],
    prior: list[EvidenceChunk],
    max_pairs: int = 10,
) -> list[tuple[EvidenceChunk, EvidenceChunk]]:
    """Pair each current chunk with its most similar prior chunk using a placeholder heuristic."""
    if not current or not prior or max_pairs <= 0:
        return []

    pairs: list[tuple[EvidenceChunk, EvidenceChunk]] = []
    for current_chunk in current[:max_pairs]:
        best_prior = max(
            prior,
            key=lambda prior_chunk: _placeholder_similarity(current_chunk, prior_chunk),
        )
        pairs.append((current_chunk, best_prior))

    return pairs


def classify_change(current: EvidenceChunk, prior: EvidenceChunk) -> DisclosureChange | None:
    # TODO: replace with Qwen2.5-14B call via Gateway; real confidence values should
    # TODO: replace this placeholder when Qwen-14B is integrated.
    # TODO: replace with gateway client when services/agent-api/app/clients/gateway.py is available.
    return DisclosureChange(
        ticker=current.ticker,
        section=current.section,
        change_type=_placeholder_change_type(),
        old_citation=build_citation(prior),
        new_citation=build_citation(current),
        summary=(
            "Placeholder disclosure change classification. "
            "The current filing appears to use stronger language than the prior filing."
        ),
        severity=0.5,
        confidence=0.7,
    )


def build_citation(chunk: EvidenceChunk) -> Citation:
    """Map an evidence chunk into the narrower citation schema."""
    return Citation(
        chunk_id=chunk.chunk_id,
        citation_anchor=chunk.citation_anchor,
        source_url=chunk.source_url,
        filed_at=chunk.filed_at,
        ticker=chunk.ticker,
        filing_type=chunk.filing_type,
        section=chunk.section,
    )


async def disclosure_change(state: AnalysisState) -> AnalysisState:
    """
    Compares chunks from the most recent filing to the prior filing
    for each (ticker, section) pair and produces a list of
    DisclosureChange objects describing material changes.

    Falls back to an empty list of changes if anything goes wrong.
    """
    try:
        if not state.retrieved_chunks:
            logger.warning("Disclosure change skipped because retrieved_chunks is empty.")
            return state.model_copy(update={"disclosure_changes": []})

        grouped_chunks = group_chunks_by_ticker_section(state.retrieved_chunks)
        results: list[DisclosureChange] = []

        for (ticker, section), group in grouped_chunks.items():
            current_chunks, prior_chunks = split_current_vs_prior(group)
            if not prior_chunks:
                logger.info(
                    "Skipping disclosure comparison because no prior filing was found.",
                    extra={"ticker": ticker, "section": section},
                )
                continue

            chunk_pairs = find_chunk_pairs(
                current_chunks,
                prior_chunks,
                max_pairs=MAX_PAIRS_PER_GROUP,
            )
            for current_chunk, prior_chunk in chunk_pairs:
                change = classify_change(current_chunk, prior_chunk)
                if change is not None:
                    results.append(change)

        filtered_results = [
            change for change in results if change.confidence >= MIN_CONFIDENCE
        ]
        return state.model_copy(update={"disclosure_changes": filtered_results})
    except Exception as exc:
        logger.warning("Disclosure change node fell back to empty results: %s", exc)
        return state.model_copy(update={"disclosure_changes": []})


def _placeholder_similarity(current: EvidenceChunk, prior: EvidenceChunk) -> int:
    # TODO: replace with embedding-based or BM25 similarity.
    shared_words = _tokenize(current.text) & _tokenize(prior.text)
    chunk_index_bonus = 5 if current.chunk_index == prior.chunk_index else 0
    return len(shared_words) + chunk_index_bonus


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))


def _parse_filed_at(value: str) -> date:
    return date.fromisoformat(value)


def _placeholder_change_type() -> ChangeType:
    return "intensified_language"
