from __future__ import annotations

import pandas as pd
import gradio as gr

from api_client import AgentApiClient


def build_documents_tab(client: AgentApiClient) -> None:
    with gr.Tab("Filing Explorer"):
        ticker = gr.Textbox(label="Ticker", value="AMD")
        fetch = gr.Button("Load Documents")
        table = gr.Dataframe(label="Documents", interactive=False)
        raw = gr.JSON(label="Documents Payload")

        def load_documents(symbol: str):
            payload = client.documents(symbol)
            documents = payload.get("documents", payload if isinstance(payload, list) else [])
            return pd.DataFrame(documents), payload

        fetch.click(load_documents, inputs=[ticker], outputs=[table, raw])
