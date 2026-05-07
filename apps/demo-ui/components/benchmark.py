from __future__ import annotations

import pandas as pd
import gradio as gr

from api_client import AgentApiClient


def build_benchmark_tab(client: AgentApiClient) -> None:
    with gr.Tab("AMD Benchmark"):
        refresh = gr.Button("Refresh Benchmark Metrics")
        table = gr.Dataframe(label="Model Metrics", interactive=False)
        raw = gr.JSON(label="Raw Benchmark Payload")

        def load_metrics():
            payload = client.benchmark_metrics()
            rows = []
            for model_name, metrics in payload.get("models", {}).items():
                row = {"model": model_name}
                row.update(metrics)
                rows.append(row)
            return pd.DataFrame(rows), payload

        refresh.click(load_metrics, outputs=[table, raw])
