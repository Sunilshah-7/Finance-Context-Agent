from __future__ import annotations

import pandas as pd
import gradio as gr

from api_client import AgentApiClient


def build_memo_tab(client: AgentApiClient) -> None:
    with gr.Tab("Analyst Memo"):
        portfolio_id = gr.Textbox(label="Portfolio ID")
        job_id = gr.Textbox(label="Job ID (optional)")
        fetch = gr.Button("Load Memo")
        memo_md = gr.Markdown(label="Memo")
        citations = gr.Dataframe(label="Evidence Table", interactive=False)

        def load_memo(portfolio: str, job: str):
            payload = client.findings(portfolio, job or None)
            memo = payload.get("memo") or {}
            markdown = "\n\n".join(
                [
                    "## Executive Summary",
                    memo.get("executive_summary", "No memo available."),
                    "## Limitations",
                    memo.get("limitations", "No limitations provided."),
                    "## Disclaimer",
                    memo.get("disclaimer", "Investment research disclaimer missing."),
                ]
            )
            return markdown, pd.DataFrame(memo.get("evidence_table", []))

        fetch.click(load_memo, inputs=[portfolio_id, job_id], outputs=[memo_md, citations])
