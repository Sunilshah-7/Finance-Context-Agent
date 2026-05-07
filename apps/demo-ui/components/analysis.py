from __future__ import annotations

import gradio as gr

from api_client import AgentApiClient


def build_analysis_tab(client: AgentApiClient) -> None:
    with gr.Tab("Analysis"):
        portfolio_id = gr.Textbox(label="Portfolio ID")
        analysis_type = gr.Dropdown(
            label="Analysis Type",
            choices=["latest_filings", "portfolio_review", "custom_question"],
            value="latest_filings",
        )
        question = gr.Textbox(label="Question", placeholder="Optional custom question")
        run = gr.Button("Start Analysis", variant="primary")
        job_id = gr.Textbox(label="Job ID", interactive=False)
        status = gr.JSON(label="Job Status")
        timer = gr.Timer(value=2, active=False)

        def start_analysis(portfolio: str, analysis_kind: str, prompt: str):
            payload = client.analyze(portfolio, analysis_kind, prompt)
            return payload["job_id"], payload, gr.update(active=True)

        def poll_status(current_job_id: str):
            if not current_job_id:
                return gr.skip(), gr.update(active=False)
            payload = client.job_status(current_job_id)
            active = payload.get("status") not in {"completed", "failed"}
            return payload, gr.update(active=active)

        run.click(start_analysis, inputs=[portfolio_id, analysis_type, question], outputs=[job_id, status, timer])
        timer.tick(poll_status, inputs=[job_id], outputs=[status, timer])
