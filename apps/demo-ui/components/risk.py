from __future__ import annotations

import pandas as pd
import gradio as gr

from api_client import AgentApiClient


def build_risk_tab(client: AgentApiClient) -> None:
    with gr.Tab("Risk Scores"):
        portfolio_id = gr.Textbox(label="Portfolio ID")
        job_id = gr.Textbox(label="Job ID (optional)")
        fetch = gr.Button("Load Risk Scores")
        table = gr.Dataframe(label="Risk Scores", interactive=False)
        raw = gr.JSON(label="Findings Payload")

        def load_risk(portfolio: str, job: str):
            payload = client.findings(portfolio, job or None)
            rows = []
            for score in payload.get("risk_scores", []):
                rows.append(
                    {
                        "ticker": score.get("ticker"),
                        "overall_score": score.get("overall_score"),
                        "score_delta": score.get("score_delta"),
                        "confidence": score.get("confidence"),
                    }
                )
            return pd.DataFrame(rows), payload

        fetch.click(load_risk, inputs=[portfolio_id, job_id], outputs=[table, raw])
