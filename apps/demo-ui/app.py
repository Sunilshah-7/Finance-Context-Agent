from __future__ import annotations

import gradio as gr

from api_client import AgentApiClient
from components.analysis import build_analysis_tab
from components.benchmark import build_benchmark_tab
from components.chat import build_chat_tab
from components.diff import build_diff_tab
from components.documents import build_documents_tab
from components.memo import build_memo_tab
from components.portfolio import build_portfolio_tab
from components.risk import build_risk_tab


client = AgentApiClient()


with gr.Blocks(title="FinContext Agent", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # FinContext Agent
        Citation-grounded portfolio analysis built for the AMD Developer Hackathon.

        Use the tabs below to upload a portfolio, trigger analysis jobs, inspect filing evidence,
        review disclosure changes, and monitor AMD benchmark metrics.
        """
    )
    build_portfolio_tab(client)
    build_analysis_tab(client)
    build_documents_tab(client)
    build_diff_tab(client)
    build_risk_tab(client)
    build_memo_tab(client)
    build_chat_tab(client)
    build_benchmark_tab(client)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
