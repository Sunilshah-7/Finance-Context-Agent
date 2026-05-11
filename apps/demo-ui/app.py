"""Gradio demo UI for FinContext Agent.

This file assembles the HuggingFace Spaces interface. It is intentionally
evidence-first: the UI can load without a live backend, but it never pretends
sample data is measured output. All real product actions go through the Agent
API client in `api_client.py`.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd
from dotenv import load_dotenv

from api_client import AgentApiClient, ApiResult


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_PORTFOLIO_PATH = REPO_ROOT / "demo" / "seed_portfolio.csv"
DISCLAIMER = "This output is research assistance only and does not constitute investment advice."
DEFAULT_QUESTION = (
    "What changed in supply-chain, export-control, or customer-concentration "
    "risk for my semiconductor holdings?"
)


def client() -> AgentApiClient:
    return AgentApiClient()


def load_seed_portfolio() -> pd.DataFrame:
    """Load the committed seed portfolio without requiring the backend."""

    if not SEED_PORTFOLIO_PATH.exists():
        return pd.DataFrame(columns=["ticker", "shares", "market_value", "sector"])
    return pd.read_csv(SEED_PORTFOLIO_PATH)


def backend_snapshot() -> tuple[str, str]:
    """Return HTML for the header and a concise status message."""

    api = client()
    result = api.health()
    if not result.ok:
        header = render_topbar("Offline", "bad", "local preview", api.base_url, result.message)
        return header, render_notice("Backend unavailable", result.message, "warn")

    data = result.data if isinstance(result.data, dict) else {}
    chunks = data.get("chunks_indexed", "unknown")
    gpu = data.get("gpu", "AMD backend")
    status = str(data.get("status", "ok")).upper()
    detail = f"{gpu} · chunks indexed: {chunks}"
    header = render_topbar(status, "ok", "amd-dev-cloud", api.base_url, detail)
    return header, render_notice("Backend connected", detail, "ok")


def render_topbar(status: str, tone: str, environment: str, base_url: str, detail: str) -> str:
    return f"""
    <div class="fc-topbar">
      <div class="fc-brand-mark">FC</div>
      <div class="fc-brand-copy">
        <div class="fc-brand-name">FinContext Agent</div>
        <div class="fc-brand-sub">SEC Disclosure Drift</div>
      </div>
      <div class="fc-top-spacer"></div>
      <div class="fc-kv"><span>env</span><strong>{escape_html(environment)}</strong></div>
      <div class="fc-kv"><span>api</span><strong>{escape_html(base_url)}</strong></div>
      <div class="fc-status fc-status-{tone}"><i></i>{escape_html(status)}</div>
    </div>
    <div class="fc-status-strip">{escape_html(detail)}</div>
    """


def render_notice(title: str, message: str, tone: str = "muted") -> str:
    return f"""
    <div class="fc-notice fc-notice-{tone}">
      <strong>{escape_html(title)}</strong>
      <span>{escape_html(message)}</span>
    </div>
    """


def escape_html(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def dataframe_from_records(records: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(records).reindex(columns=columns)


def format_api_result(result: ApiResult, success_title: str) -> str:
    if result.ok:
        return render_notice(success_title, "Agent API returned a successful response.", "ok")
    return render_notice("Agent API request failed", result.message, "warn")


def render_json_block(payload: dict[str, Any] | list[Any] | None) -> str:
    if payload is None:
        return "<pre class='fc-json'>No response payload.</pre>"
    import json

    return f"<pre class='fc-json'>{escape_html(json.dumps(payload, indent=2, sort_keys=True))}</pre>"


def build_app() -> gr.Blocks:
    """Create the Gradio Blocks app without launching it."""

    header_html, status_html = backend_snapshot()
    seed_df = load_seed_portfolio()

    with gr.Blocks(
        title="FinContext Agent",
        theme=gr.themes.Base(
            primary_hue="slate",
            neutral_hue="slate",
            font=["IBM Plex Sans", "Inter", "Arial", "sans-serif"],
            font_mono=["IBM Plex Mono", "Menlo", "monospace"],
        ),
        css=CUSTOM_CSS,
    ) as demo:
        gr.HTML(header_html)

        with gr.Row(elem_classes=["fc-hero-row"]):
            with gr.Column(scale=2):
                gr.Markdown(
                    """
                    # SEC disclosure drift research console
                    Trace portfolio risk back to exact filing paragraphs, compare changed language, and keep every analyst claim tied to evidence.
                    """
                )
            with gr.Column(scale=1):
                gr.HTML(status_html)

        with gr.Tabs(elem_classes=["fc-tabs"]):
            with gr.Tab("01 Portfolio"):
                build_portfolio_tab(seed_df)
            with gr.Tab("02 Analysis Run"):
                build_analysis_tab()
            with gr.Tab("03 Disclosure Drift"):
                build_drift_tab()
            with gr.Tab("04 Evidence Explorer"):
                build_evidence_tab()
            with gr.Tab("05 Risk Scores"):
                build_risk_tab()
            with gr.Tab("06 Analyst Memo"):
                build_memo_tab()
            with gr.Tab("07 AMD Benchmark"):
                build_benchmark_tab()

        gr.Markdown(f"<div class='fc-disclaimer'>{DISCLAIMER}</div>")

    return demo


def build_portfolio_tab(seed_df: pd.DataFrame) -> None:
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">Portfolio input</div>
          <p>Upload a CSV to create a portfolio in Agent API, or inspect the committed seed portfolio while the backend is offline.</p>
        </div>
        """
    )
    with gr.Row():
        with gr.Column(scale=2):
            gr.Dataframe(seed_df, label="Seed holdings", interactive=False, wrap=True)
        with gr.Column(scale=1):
            portfolio_name = gr.Textbox(value="Demo Portfolio", label="Portfolio name")
            upload_file = gr.File(label="Portfolio CSV", file_types=[".csv"], type="filepath")
            upload_button = gr.Button("Upload Portfolio", variant="primary")
            upload_status = gr.HTML(render_notice("Waiting for upload", "Choose a CSV and call the Agent API.", "muted"))
            upload_payload = gr.HTML(render_json_block(None))

    upload_button.click(
        upload_portfolio_action,
        inputs=[upload_file, portfolio_name],
        outputs=[upload_status, upload_payload],
    )


def build_analysis_tab() -> None:
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">Analysis run</div>
          <p>Start a portfolio analysis job, then poll the documented job endpoint for stage and progress.</p>
        </div>
        """
    )
    with gr.Row():
        with gr.Column(scale=2):
            portfolio_id = gr.Textbox(label="Portfolio ID", placeholder="p_abc123")
            question = gr.Textbox(
                value=DEFAULT_QUESTION,
                label="Analyst question",
                lines=3,
            )
            start_button = gr.Button("Start Analysis", variant="primary")
        with gr.Column(scale=1):
            job_id = gr.Textbox(label="Job ID", placeholder="job_xyz789")
            refresh_button = gr.Button("Refresh Job Status")

    with gr.Row():
        analysis_status = gr.HTML(render_notice("No job started", "Start an analysis or enter a job ID to check status.", "muted"))
        analysis_payload = gr.HTML(render_json_block(None))

    start_button.click(
        start_analysis_action,
        inputs=[portfolio_id, question],
        outputs=[analysis_status, analysis_payload, job_id],
    )
    refresh_button.click(
        refresh_job_action,
        inputs=[job_id],
        outputs=[analysis_status, analysis_payload],
    )


def upload_portfolio_action(file_path: str | None, portfolio_name: str) -> tuple[str, str]:
    if not file_path:
        return render_notice("Missing CSV", "Choose a portfolio CSV before uploading.", "warn"), render_json_block(None)
    result = client().upload_portfolio(file_path, portfolio_name or "Demo Portfolio")
    return format_api_result(result, "Portfolio uploaded"), render_json_block(result.data)


def start_analysis_action(portfolio_id: str, question: str) -> tuple[str, str, str]:
    if not portfolio_id.strip():
        return (
            render_notice("Missing portfolio ID", "Upload or enter a portfolio ID before starting analysis.", "warn"),
            render_json_block(None),
            "",
        )
    result = client().start_analysis(portfolio_id, question)
    data = result.data if isinstance(result.data, dict) else {}
    next_job_id = str(data.get("job_id", "")) if result.ok else ""
    return format_api_result(result, "Analysis queued"), render_json_block(result.data), next_job_id


def refresh_job_action(job_id: str) -> tuple[str, str]:
    if not job_id.strip():
        return render_notice("Missing job ID", "Enter a job ID to refresh status.", "warn"), render_json_block(None)
    result = client().get_job(job_id)
    return format_api_result(result, "Job status loaded"), render_json_block(result.data)


def build_drift_tab() -> None:
    gr.HTML(render_notice("Disclosure drift wiring pending", "This shell will render citation-backed changes from GET /api/diff/{ticker}.", "muted"))


def build_evidence_tab() -> None:
    gr.HTML(render_notice("Evidence explorer wiring pending", "This shell will show filing documents and citation-ready chunks when the backend is available.", "muted"))


def build_risk_tab() -> None:
    gr.HTML(render_notice("Risk score wiring pending", "This shell will render research risk scores from GET /api/findings/{portfolio_id}.", "muted"))


def build_memo_tab() -> None:
    gr.HTML(render_notice("Memo wiring pending", "This shell will render the analyst memo and evidence table after an analysis completes.", "muted"))


def build_benchmark_tab() -> None:
    gr.HTML(render_notice("Benchmark wiring pending", "This shell will display measured AMD VM metrics only when the backend reports them.", "muted"))


CUSTOM_CSS = """
:root {
  --fc-bg: #fafaf7;
  --fc-panel: #ffffff;
  --fc-sunk: #f4f3ee;
  --fc-line: #e4e1d8;
  --fc-line-strong: #cfc9bc;
  --fc-ink: #15171c;
  --fc-muted: #667085;
  --fc-faint: #98a2b3;
  --fc-primary: #2f5bd7;
  --fc-green: #2e6f4b;
  --fc-amber: #b8741c;
  --fc-red: #b83232;
}

body,
.gradio-container {
  background: var(--fc-bg) !important;
  color: var(--fc-ink) !important;
}

.gradio-container {
  max-width: none !important;
  font-size: 14px !important;
}

.fc-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border: 1px solid var(--fc-line);
  background: var(--fc-panel);
  border-radius: 8px 8px 0 0;
}

.fc-brand-mark {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  background: var(--fc-ink);
  color: var(--fc-panel);
  font: 700 12px "IBM Plex Mono", monospace;
}

.fc-brand-name {
  font-weight: 700;
  letter-spacing: -0.01em;
}

.fc-brand-sub,
.fc-kv,
.fc-status-strip {
  font: 500 11px "IBM Plex Mono", monospace;
  color: var(--fc-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.fc-top-spacer {
  flex: 1;
}

.fc-kv {
  display: flex;
  gap: 6px;
  text-transform: none;
}

.fc-kv span {
  color: var(--fc-faint);
}

.fc-kv strong {
  color: var(--fc-ink);
  font-weight: 600;
}

.fc-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 24px;
  padding: 0 9px;
  border-radius: 4px;
  font: 700 11px "IBM Plex Mono", monospace;
  letter-spacing: 0.04em;
}

.fc-status i {
  width: 7px;
  height: 7px;
  border-radius: 99px;
  display: block;
}

.fc-status-ok {
  background: #e2f0e5;
  color: var(--fc-green);
}

.fc-status-ok i {
  background: var(--fc-green);
}

.fc-status-bad {
  background: #fce6e4;
  color: var(--fc-red);
}

.fc-status-bad i {
  background: var(--fc-red);
}

.fc-status-strip {
  padding: 8px 18px;
  border: 1px solid var(--fc-line);
  border-top: 0;
  background: var(--fc-sunk);
  border-radius: 0 0 8px 8px;
  text-transform: none;
}

.fc-hero-row {
  margin: 16px 0 8px;
}

.fc-hero-row h1 {
  margin-bottom: 4px;
  font-size: 26px;
  letter-spacing: -0.03em;
}

.fc-hero-row p {
  color: var(--fc-muted);
  max-width: 820px;
}

.fc-notice {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  border: 1px solid var(--fc-line);
  border-left-width: 4px;
  border-radius: 6px;
  background: var(--fc-panel);
}

.fc-notice span {
  color: var(--fc-muted);
  font-size: 13px;
}

.fc-notice-ok {
  border-left-color: var(--fc-green);
}

.fc-notice-warn {
  border-left-color: var(--fc-amber);
}

.fc-notice-muted {
  border-left-color: var(--fc-line-strong);
}

.fc-panel {
  border: 1px solid var(--fc-line);
  border-radius: 8px;
  background: var(--fc-panel);
  padding: 14px;
}

.fc-panel-title {
  font: 700 12px "IBM Plex Mono", monospace;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fc-muted);
  margin-bottom: 10px;
}

.fc-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 7px;
  border: 1px solid var(--fc-line);
  border-radius: 4px;
  font: 600 11px "IBM Plex Mono", monospace;
  background: var(--fc-sunk);
}

.fc-citation {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  background: #e8eefb;
  color: #1e3e96;
  font: 600 11px "IBM Plex Mono", monospace;
}

.fc-disclaimer {
  margin-top: 18px;
  color: var(--fc-muted);
  font-size: 12px;
  border-top: 1px solid var(--fc-line);
  padding-top: 12px;
}

.fc-tabs button {
  font-weight: 650 !important;
}

table {
  font-size: 13px !important;
}

.fc-json {
  margin: 0;
  padding: 12px;
  max-height: 360px;
  overflow: auto;
  border: 1px solid var(--fc-line);
  border-radius: 6px;
  background: #111317;
  color: #e8eaf0;
  font: 12px "IBM Plex Mono", monospace;
}
"""


if __name__ == "__main__":
    build_app().launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
