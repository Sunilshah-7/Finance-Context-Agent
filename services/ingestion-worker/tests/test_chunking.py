"""Chunking tests for bounds, overlap, table isolation, and citations."""

from __future__ import annotations

import re

from worker.chunking import chunk_document
from worker.models import NormalizedDocument, NormalizedSection


def test_chunk_document_enforces_bounds_overlap_tables_and_citations():
    words = [f"risk{i}" for i in range(260)]
    text = "\n\n".join(
        [
            " ".join(words[:90]),
            " ".join(words[90:180]),
            " ".join(words[180:]),
        ]
    )
    document = NormalizedDocument(
        document_id="doc_1",
        ticker="AMD",
        cik="0000002488",
        company_name="Advanced Micro Devices, Inc.",
        filing_type="10-K",
        accession_number="0000002488-25-000012",
        filed_at="2025-02-14",
        fiscal_period="FY2024",
        source_url="https://www.sec.gov/example",
        sections=[
            NormalizedSection(
                section_id="item_1a",
                item_label="Item 1A",
                title="Risk Factors",
                text=text,
                tables=["Risk | Impact\nSupply | High"],
                word_count=len(text.split()),
            )
        ],
    )

    chunks = chunk_document(
        document,
        target_min_tokens=50,
        target_max_tokens=90,
        max_tokens=120,
        min_tokens=20,
        overlap_tokens=10,
    )

    assert len(chunks) >= 3
    assert all(chunk.token_count <= 120 for chunk in chunks)
    assert re.match(r"AMD 10-K Item 1A paragraph \d+", chunks[0].citation_anchor)
    assert chunks[-1].is_table is True
    assert chunks[-1].citation_anchor == "AMD 10-K Item 1A table 1"
    assert len(chunks[0].text_hash) == 16
    assert set(chunks[0].text.split()[-20:]) & set(chunks[1].text.split()[:30])
