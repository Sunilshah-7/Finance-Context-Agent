from __future__ import annotations

import gradio as gr

from api_client import AgentApiClient


def build_chat_tab(client: AgentApiClient) -> None:
    with gr.Tab("Chat"):
        portfolio_id = gr.Textbox(label="Portfolio ID")
        question = gr.Textbox(label="Question", lines=3)
        ask = gr.Button("Ask")
        answer = gr.Markdown(label="Streaming Answer")

        def stream_answer(portfolio: str, prompt: str):
            if not portfolio or not prompt:
                yield "Enter a portfolio ID and question."
                return
            for partial in client.stream_chat(portfolio, prompt):
                yield partial

        ask.click(stream_answer, inputs=[portfolio_id, question], outputs=[answer])
