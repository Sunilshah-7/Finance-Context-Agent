from __future__ import annotations

import gradio as gr

from api_client import AgentApiClient


def build_portfolio_tab(client: AgentApiClient) -> None:
    with gr.Tab("Portfolio Upload"):
        name = gr.Textbox(label="Portfolio Name", value="Demo Portfolio")
        file = gr.File(label="Portfolio CSV", file_types=[".csv"])
        submit = gr.Button("Upload Portfolio", variant="primary")
        response = gr.JSON(label="Upload Response")
        holdings = gr.Dataframe(label="Tickers", interactive=False)

        def on_upload(portfolio_name: str, file_obj):
            if file_obj is None:
                return {"error": "Upload a CSV file first."}, None
            payload = client.upload_portfolio(portfolio_name, file_obj.name)
            return payload, client.holdings_dataframe(payload)

        submit.click(on_upload, inputs=[name, file], outputs=[response, holdings])
