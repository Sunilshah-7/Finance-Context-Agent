from __future__ import annotations

from app.retrieval import apply_section_diversity
from tests.test_nodes import sample_chunk


def test_apply_section_diversity_caps_per_section() -> None:
    chunks = [
        sample_chunk(str(index), "2025-01-01", "text").model_copy(update={"chunk_index": index})
        for index in range(5)
    ]
    selected = apply_section_diversity(chunks, max_per_section_per_ticker=3, limit=12)
    assert len(selected) == 3
