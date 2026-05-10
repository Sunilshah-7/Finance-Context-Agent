"""Validation CLI tests using temporary SQLite and mocked Qdrant checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import validate_ingestion
from worker.db import upsert_chunks, upsert_document
from worker.models import ChunkInput, NormalizedDocument, NormalizedSection
from worker.validation import QdrantCountValidation


def test_validation_cli_reports_success_with_document_summary(
    tmp_path,
    monkeypatch,
    capsys,
):
    db_path = _seed_db(tmp_path, citation_anchor="AMD 10-K Item 1A paragraph 1")
    monkeypatch.setattr(
        validate_ingestion,
        "validate_qdrant_count",
        lambda *_, **__: QdrantCountValidation(
            sqlite_chunks_count=1,
            qdrant_points_count=1,
            collection="fincontext_chunks",
        ),
    )

    exit_code = validate_ingestion.main(
        [
            "--db-path",
            str(db_path),
            "--ticker",
            "AMD",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "SQLite FTS is in sync: 1 chunks" in output
    assert "Citation anchors valid for 1 sampled chunks" in output
    assert "AMD 10-K 2025-02-14: 1 chunks; sections=Item 1A" in output


def test_validation_cli_returns_failure_for_invalid_citation(tmp_path, capsys):
    db_path = _seed_db(tmp_path, citation_anchor="AMD 10-K Item 1A table 1")

    exit_code = validate_ingestion.main(
        [
            "--db-path",
            str(db_path),
            "--skip-qdrant",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Citation anchor inspection failed" in output


def _seed_db(tmp_path: Path, citation_anchor: str) -> Path:
    schema_path = Path(__file__).resolve().parents[3] / "infra" / "schema.sql"
    db_path = tmp_path / "fincontext.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    upsert_document(conn, _document())
    upsert_chunks(conn, [_chunk(citation_anchor)])
    conn.commit()
    conn.close()
    return db_path


def _document() -> NormalizedDocument:
    return NormalizedDocument(
        document_id="doc_1",
        ticker="AMD",
        cik="0000002488",
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
                text="Supply chain risk text.",
                word_count=4,
            )
        ],
    )


def _chunk(citation_anchor: str) -> ChunkInput:
    return ChunkInput(
        chunk_id="chunk_1",
        document_id="doc_1",
        ticker="AMD",
        cik="0000002488",
        filing_type="10-K",
        accession_number="0000002488-25-000012",
        filed_at="2025-02-14",
        fiscal_period="FY2024",
        section="item_1a",
        item_label="Item 1A",
        section_title="Risk Factors",
        chunk_index=0,
        text="Supply chain risk text.",
        text_hash="hash_1",
        token_count=5,
        citation_anchor=citation_anchor,
        source_url="https://www.sec.gov/example",
    )
