from __future__ import annotations

import gradio as gr

from api_client import AgentApiClient


def build_diff_tab(client: AgentApiClient) -> None:
    with gr.Tab("Disclosure Diff"):
        ticker = gr.Textbox(label="Ticker", value="AMD")
        section = gr.Dropdown(label="Section", choices=["Item 1", "Item 1A", "Item 7", "Item 7A", "Item 8"], value="Item 1A")
        year_a = gr.Textbox(label="Year A", value="2023")
        year_b = gr.Textbox(label="Year B", value="2025")
        filing_type = gr.Dropdown(label="Filing Type", choices=["10-K", "10-Q"], value="10-K")
        fetch = gr.Button("Load Diff", variant="primary")
        diff_json = gr.JSON(label="Diff Data")
        summary = gr.Markdown(label="Change Cards")

        def load_diff(symbol: str, section_name: str, earlier: str, later: str, doc_type: str):
            payload = client.diff(symbol, section_name, earlier, later, doc_type)
            cards = []
            for change in payload.get("changes", []):
                cards.append(
                    "\n".join(
                        [
                            f"### {change.get('change_type', 'change').replace('_', ' ').title()}",
                            f"Materiality: `{change.get('materiality', 'unknown')}`",
                            f"Confidence: `{change.get('confidence', 0):.2f}`",
                            change.get("summary", ""),
                            f"New citation: `{change.get('new_citation_anchor') or 'n/a'}`",
                        ]
                    )
                )
            return payload, "\n\n".join(cards) or "No material changes returned."

        fetch.click(load_diff, inputs=[ticker, section, year_a, year_b, filing_type], outputs=[diff_json, summary])
