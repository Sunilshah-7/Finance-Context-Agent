from __future__ import annotations

import json
from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
ALLOWED_CHANGE_TYPES = {
    "new_risk",
    "removed_risk",
    "intensified_language",
    "softened_language",
    "metric_changed",
    "legal_accounting_update",
}


def test_labeled_queries_fixture_shape():
    queries = _load_fixture("labeled_queries.json")

    assert len(queries) == 20
    ids = {item["id"] for item in queries}
    assert len(ids) == len(queries)
    for item in queries:
        assert item["id"].startswith("rq_")
        assert item["query"]
        assert item["intent"]
        assert item["target_tickers"]
        assert item["filing_types"]
        assert item["sections"]
        assert item["bm25_keywords"]
        assert item["expected_evidence_hints"]
        assert item["expected_chunk_ids"] == []
        assert item["label_status"] == "planned_pending_ingestion"


def test_known_changes_fixture_shape():
    changes = _load_fixture("known_changes.json")

    assert len(changes) == 10
    ids = {item["id"] for item in changes}
    assert len(ids) == len(changes)
    for item in changes:
        assert item["id"].startswith("kc_")
        assert item["ticker"]
        assert item["section"].startswith("item_")
        assert item["filing_type"] in {"10-K", "10-Q"}
        assert item["year_a"] < item["year_b"]
        assert item["expected_change_type"] in ALLOWED_CHANGE_TYPES
        assert item["risk_theme"]
        assert item["evidence_hints"]
        assert item["old_citation_anchor"] is None
        assert item["new_citation_anchor"] is None
        assert item["label_status"] == "planned_pending_ingestion"


def _load_fixture(filename: str):
    path = FIXTURES_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))
