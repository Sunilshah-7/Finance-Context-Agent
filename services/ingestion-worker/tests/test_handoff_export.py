"""Tests for exporting citation-ready chunk samples for teammate handoff."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from worker.handoff_export import (
    HandoffFilters,
    build_handoff_export,
    parse_csv_filter,
    write_handoff_export,
)


def create_sample_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "fincontext.db"
    schema_path = Path(__file__).resolve().parents[3] / "infra" / "schema.sql"
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO documents (
            id, ticker, cik, company_name, filing_type, accession_number,
            filed_at, fiscal_period, source_url, sections_parsed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "doc_amd_2025",
            "AMD",
            "0000002488",
            "Advanced Micro Devices, Inc.",
            "10-K",
            "0000002488-25-000012",
            "2025-02-14",
            "FY2024",
            "https://www.sec.gov/amd",
            json.dumps(["Item 1A", "Item 7"]),
        ),
    )
    conn.executemany(
        """
        INSERT INTO chunks (
            id, document_id, ticker, filing_type, filed_at, section, item_label,
            section_title, chunk_index, text, text_hash, token_count,
            citation_anchor, source_url, is_table, vector_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "chunk_1",
                "doc_amd_2025",
                "AMD",
                "10-K",
                "2025-02-14",
                "item_1a",
                "Item 1A",
                "Risk Factors",
                0,
                "Supply chain risk text " * 20,
                "hash_1",
                80,
                "AMD 10-K Item 1A paragraph 1",
                "https://www.sec.gov/amd",
                0,
                "chunk_1",
            ),
            (
                "chunk_2",
                "doc_amd_2025",
                "AMD",
                "10-K",
                "2025-02-14",
                "item_7",
                "Item 7",
                "Management Discussion",
                1,
                "Liquidity discussion text.",
                "hash_2",
                12,
                "AMD 10-K Item 7 paragraph 1",
                "https://www.sec.gov/amd",
                0,
                "chunk_2",
            ),
        ],
    )
    conn.commit()
    return conn


def test_build_handoff_export_filters_and_formats_chunks(tmp_path):
    conn = create_sample_db(tmp_path)

    payload = build_handoff_export(
        conn,
        filters=HandoffFilters(
            tickers=["AMD"],
            filing_types=["10-K"],
            sections=["Item 1A"],
            limit=5,
            preview_chars=40,
        ),
    )

    assert payload["counts"] == {"documents": 1, "chunks": 1}
    assert payload["documents"][0]["document_id"] == "doc_amd_2025"
    assert payload["documents"][0]["sections_parsed"] == ["Item 1A", "Item 7"]

    chunk = payload["chunks"][0]
    assert chunk["chunk_id"] == "chunk_1"
    assert chunk["qdrant_point_id"] == "chunk_1"
    assert chunk["citation_anchor"] == "AMD 10-K Item 1A paragraph 1"
    assert chunk["source_url"] == "https://www.sec.gov/amd"
    assert chunk["text_preview"].endswith("...")
    assert "text" not in chunk


def test_build_handoff_export_can_include_full_text(tmp_path):
    conn = create_sample_db(tmp_path)

    payload = build_handoff_export(
        conn,
        filters=HandoffFilters(limit=1, include_full_text=True),
    )

    assert payload["chunks"][0]["text"].startswith("Supply chain risk text")


def test_write_handoff_export_writes_json_file(tmp_path):
    output_path = tmp_path / "handoff.json"
    payload = {"chunks": [{"chunk_id": "chunk_1"}]}

    write_handoff_export(payload, str(output_path))

    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_export_handoff_cli_writes_filtered_json(tmp_path):
    conn = create_sample_db(tmp_path)
    conn.close()
    output_path = tmp_path / "handoff.json"
    cli_path = Path(__file__).resolve().parents[1] / "export_handoff.py"

    subprocess.run(
        [
            sys.executable,
            str(cli_path),
            "--db-path",
            str(tmp_path / "fincontext.db"),
            "--output",
            str(output_path),
            "--tickers",
            "AMD",
            "--sections",
            "Item 7",
            "--limit",
            "5",
        ],
        check=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["counts"] == {"documents": 1, "chunks": 1}
    assert payload["chunks"][0]["citation_anchor"] == "AMD 10-K Item 7 paragraph 1"


def test_parse_csv_filter_normalizes_empty_values():
    assert parse_csv_filter("AMD, NVDA,,") == ["AMD", "NVDA"]
    assert parse_csv_filter("") is None
