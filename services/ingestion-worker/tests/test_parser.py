"""SEC HTML parser tests using minimal inline filing fragments."""

from __future__ import annotations

from pathlib import Path

from worker.parsers.sec_html import extract_sections


def test_extract_sections_from_minimal_sec_html():
    html = """
    <html><body>
      <h2>Item 1. Business</h2>
      <p>We design processors and adaptive computing products.</p>
      <h2>Item 1A. Risk Factors</h2>
      <p>Our supply chain may be adversely affected by third-party manufacturing.</p>
      <table><tr><th>Risk</th><th>Impact</th></tr><tr><td>Supply</td><td>High</td></tr></table>
      <h2>Item 7. Management's Discussion and Analysis</h2>
      <p>Revenue increased due to data center demand.</p>
    </body></html>
    """

    sections = extract_sections(html)
    by_id = {section.section_id: section for section in sections}

    assert "item_1a" in by_id
    assert "third-party manufacturing" in by_id["item_1a"].text
    assert by_id["item_1a"].item_label == "Item 1A"
    assert by_id["item_1a"].tables == ["Risk | Impact\nSupply | High"]
    assert "item_7" in by_id


def test_extract_sections_from_amd_like_item_1a_fixture():
    fixture_path = (
        Path(__file__).parent / "fixtures" / "amd_10k_item1a_fixture.html"
    )
    sections = extract_sections(fixture_path.read_text(encoding="utf-8"))
    by_id = {section.section_id: section for section in sections}

    assert "item_1a" in by_id
    assert by_id["item_1a"].word_count > 1000
    assert "third-party foundries" in by_id["item_1a"].text
    assert "Item 7" not in by_id["item_1a"].text
