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


def empty_dataframe(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


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
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">Disclosure drift</div>
          <p>Load side-by-side language changes for a ticker and filing section. The hero view is old evidence versus new evidence with citation anchors.</p>
        </div>
        """
    )
    with gr.Row():
        ticker = gr.Dropdown(["AMD", "NVDA", "MSFT", "JPM", "TSLA"], value="AMD", label="Ticker")
        section = gr.Dropdown(["Item 1", "Item 1A", "Item 7", "Item 7A", "Item 8"], value="Item 1A", label="Section")
        filing_type = gr.Dropdown(["10-K", "10-Q"], value="10-K", label="Filing type")
        year_a = gr.Textbox(value="", label="Prior year")
        year_b = gr.Textbox(value="", label="Current year")
    load_button = gr.Button("Load Disclosure Drift", variant="primary")
    status = gr.HTML(render_notice("No diff loaded", "Choose a ticker and section to query the Agent API.", "muted"))
    changes_table = gr.Dataframe(
        empty_dataframe(["change_type", "materiality", "confidence", "summary", "old_citation_anchor", "new_citation_anchor"]),
        label="Disclosure changes",
        interactive=False,
        wrap=True,
    )
    evidence_html = gr.HTML(render_notice("Evidence preview", "Select a change after loading data to inspect old and new passages.", "muted"))
    load_button.click(
        load_drift_action,
        inputs=[ticker, section, year_a, year_b, filing_type],
        outputs=[status, changes_table, evidence_html],
    )


def build_evidence_tab() -> None:
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">Evidence explorer</div>
          <p>Inspect filing records that can support citations. This tab never calls storage directly; it only uses the Agent API document endpoint.</p>
        </div>
        """
    )
    with gr.Row():
        ticker = gr.Dropdown(["AMD", "NVDA", "MSFT", "JPM", "TSLA"], value="AMD", label="Ticker")
        load_button = gr.Button("Load Documents", variant="primary")
    status = gr.HTML(render_notice("No documents loaded", "Load a ticker after ingestion has produced indexed filing data.", "muted"))
    documents = gr.Dataframe(
        empty_dataframe(["document_id", "filing_type", "filed_at", "sections_parsed", "chunks_indexed", "source_url"]),
        label="Documents",
        interactive=False,
        wrap=True,
    )
    load_button.click(load_documents_action, inputs=[ticker], outputs=[status, documents])


def build_risk_tab() -> None:
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">Risk scores</div>
          <p>Research risk scores summarize citation-backed disclosure changes. This is not investment advice and does not contain recommendations.</p>
        </div>
        """
    )
    with gr.Row():
        portfolio_id = gr.Textbox(label="Portfolio ID", placeholder="p_abc123")
        job_id = gr.Textbox(label="Job ID optional", placeholder="job_xyz789")
        load_button = gr.Button("Load Risk Scores", variant="primary")
    status = gr.HTML(render_notice("No risk scores loaded", "Load findings after an analysis job completes.", "muted"))
    scores = gr.Dataframe(
        empty_dataframe(["ticker", "overall_score", "score_delta", "confidence", "drivers", "portfolio_impact"]),
        label="Risk scores",
        interactive=False,
        wrap=True,
    )
    load_button.click(load_risk_scores_action, inputs=[portfolio_id, job_id], outputs=[status, scores])


def build_memo_tab() -> None:
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">Analyst memo</div>
          <p>Render the final memo, evidence table, limitations, citation quality, and the required research disclaimer.</p>
        </div>
        """
    )
    with gr.Row():
        portfolio_id = gr.Textbox(label="Portfolio ID", placeholder="p_abc123")
        job_id = gr.Textbox(label="Job ID optional", placeholder="job_xyz789")
        load_button = gr.Button("Load Memo", variant="primary")
    status = gr.HTML(render_notice("No memo loaded", "Load findings after an analysis job completes.", "muted"))
    memo = gr.Markdown("No memo loaded.")
    evidence = gr.Dataframe(
        empty_dataframe(["citation_id", "citation_anchor", "source_url"]),
        label="Evidence table",
        interactive=False,
        wrap=True,
    )
    load_button.click(load_memo_action, inputs=[portfolio_id, job_id], outputs=[status, memo, evidence])


def build_benchmark_tab() -> None:
    gr.HTML(
        """
        <div class="fc-panel">
          <div class="fc-panel-title">AMD benchmark</div>
          <p>Displays measured backend metrics only when the Agent API reports them. Empty values mean the AMD VM metrics path is not live yet.</p>
        </div>
        """
    )
    load_button = gr.Button("Load Benchmark Metrics", variant="primary")
    status = gr.HTML(render_notice("No metrics loaded", "Metrics require the AMD VM backend and Gateway reporting path.", "muted"))
    gpu_table = gr.Dataframe(empty_dataframe(["device", "vram_gb", "vram_used_gb"]), label="GPU", interactive=False)
    request_table = gr.Dataframe(
        empty_dataframe(["service", "count", "avg_latency_ms", "avg_tokens_per_second", "avg_time_to_first_token_ms"]),
        label="Recent request metrics",
        interactive=False,
        wrap=True,
    )
    scenario_table = gr.Dataframe(empty_dataframe(["scenario", "seconds"]), label="Benchmark scenarios", interactive=False)
    load_button.click(load_benchmark_action, outputs=[status, gpu_table, request_table, scenario_table])


def load_drift_action(
    ticker: str,
    section: str,
    year_a: str,
    year_b: str,
    filing_type: str,
) -> tuple[str, pd.DataFrame, str]:
    result = client().get_diff(ticker, section, year_a.strip() or None, year_b.strip() or None, filing_type)
    if not result.ok:
        return (
            format_api_result(result, "Disclosure drift loaded"),
            empty_dataframe(["change_type", "materiality", "confidence", "summary", "old_citation_anchor", "new_citation_anchor"]),
            render_notice("No evidence loaded", result.message, "warn"),
        )
    data = result.data if isinstance(result.data, dict) else {}
    changes = data.get("changes", [])
    table = dataframe_from_records(
        changes if isinstance(changes, list) else [],
        ["change_type", "materiality", "confidence", "summary", "old_citation_anchor", "new_citation_anchor"],
    )
    return format_api_result(result, "Disclosure drift loaded"), table, render_drift_evidence(changes)


def render_drift_evidence(changes: Any) -> str:
    if not isinstance(changes, list) or not changes:
        return render_notice("No disclosure changes", "The API returned no changes for this filter.", "muted")
    cards = []
    for change in changes[:3]:
        if not isinstance(change, dict):
            continue
        old_cite = change.get("old_citation_anchor") or "No prior citation"
        new_cite = change.get("new_citation_anchor") or "No current citation"
        cards.append(
            f"""
            <div class="fc-evidence-card">
              <div class="fc-panel-title">{escape_html(change.get("change_type", "change"))}</div>
              <p>{escape_html(change.get("summary", ""))}</p>
              <div><span class="fc-chip">Prior</span> <span class="fc-citation">{escape_html(old_cite)}</span></div>
              <blockquote>{escape_html(change.get("old_text") or "No prior passage returned.")}</blockquote>
              <div><span class="fc-chip">Current</span> <span class="fc-citation">{escape_html(new_cite)}</span></div>
              <blockquote>{escape_html(change.get("new_text") or "No current passage returned.")}</blockquote>
            </div>
            """
        )
    return "\n".join(cards)


def load_documents_action(ticker: str) -> tuple[str, pd.DataFrame]:
    result = client().get_documents(ticker)
    if not result.ok:
        return format_api_result(result, "Documents loaded"), empty_dataframe(
            ["document_id", "filing_type", "filed_at", "sections_parsed", "chunks_indexed", "source_url"]
        )
    data = result.data if isinstance(result.data, dict) else {}
    docs = data.get("documents", [])
    table = dataframe_from_records(
        docs if isinstance(docs, list) else [],
        ["document_id", "filing_type", "filed_at", "sections_parsed", "chunks_indexed", "source_url"],
    )
    return format_api_result(result, "Documents loaded"), table


def load_risk_scores_action(portfolio_id: str, job_id: str) -> tuple[str, pd.DataFrame]:
    if not portfolio_id.strip():
        return render_notice("Missing portfolio ID", "Enter a portfolio ID before loading findings.", "warn"), empty_dataframe(
            ["ticker", "overall_score", "score_delta", "confidence", "drivers", "portfolio_impact"]
        )
    result = client().get_findings(portfolio_id, job_id or None)
    if not result.ok:
        return format_api_result(result, "Risk scores loaded"), empty_dataframe(
            ["ticker", "overall_score", "score_delta", "confidence", "drivers", "portfolio_impact"]
        )
    data = result.data if isinstance(result.data, dict) else {}
    scores = data.get("risk_scores", [])
    normalized = [flatten_risk_score(item) for item in scores] if isinstance(scores, list) else []
    return format_api_result(result, "Risk scores loaded"), dataframe_from_records(
        normalized,
        ["ticker", "overall_score", "score_delta", "confidence", "drivers", "portfolio_impact"],
    )


def flatten_risk_score(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    drivers = item.get("drivers", [])
    impact = item.get("portfolio_impact", {})
    return {
        "ticker": item.get("ticker"),
        "overall_score": item.get("overall_score"),
        "score_delta": item.get("score_delta"),
        "confidence": item.get("confidence"),
        "drivers": "; ".join(driver.get("summary", "") for driver in drivers if isinstance(driver, dict)),
        "portfolio_impact": impact.get("exposure_level") if isinstance(impact, dict) else impact,
    }


def load_memo_action(portfolio_id: str, job_id: str) -> tuple[str, str, pd.DataFrame]:
    if not portfolio_id.strip():
        return (
            render_notice("Missing portfolio ID", "Enter a portfolio ID before loading the memo.", "warn"),
            "No memo loaded.",
            empty_dataframe(["citation_id", "citation_anchor", "source_url"]),
        )
    result = client().get_findings(portfolio_id, job_id or None)
    if not result.ok:
        return (
            format_api_result(result, "Memo loaded"),
            "No memo loaded because the Agent API request failed.",
            empty_dataframe(["citation_id", "citation_anchor", "source_url"]),
        )
    data = result.data if isinstance(result.data, dict) else {}
    memo = data.get("memo", {}) if isinstance(data.get("memo"), dict) else {}
    evidence_rows = memo.get("evidence_table", [])
    return (
        format_api_result(result, "Memo loaded"),
        format_memo_markdown(memo),
        dataframe_from_records(
            evidence_rows if isinstance(evidence_rows, list) else [],
            ["citation_id", "citation_anchor", "source_url"],
        ),
    )


def format_memo_markdown(memo: dict[str, Any]) -> str:
    if not memo:
        return "No memo returned by the Agent API."
    parts = [
        "## Executive Summary",
        str(memo.get("executive_summary", "No executive summary returned.")),
        "## Watchlist Questions",
    ]
    questions = memo.get("watchlist_questions", [])
    if isinstance(questions, list) and questions:
        parts.extend(f"- {question}" for question in questions)
    else:
        parts.append("- No watchlist questions returned.")
    parts.extend(
        [
            "## Limitations",
            str(memo.get("limitations", "No limitations returned.")),
            "## Disclaimer",
            str(memo.get("disclaimer") or DISCLAIMER),
        ]
    )
    return "\n\n".join(parts)


def load_benchmark_action() -> tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    result = client().get_benchmark_metrics()
    if not result.ok:
        return (
            format_api_result(result, "Benchmark metrics loaded"),
            empty_dataframe(["device", "vram_gb", "vram_used_gb"]),
            empty_dataframe(["service", "count", "avg_latency_ms", "avg_tokens_per_second", "avg_time_to_first_token_ms"]),
            empty_dataframe(["scenario", "seconds"]),
        )
    data = result.data if isinstance(result.data, dict) else {}
    gpu = data.get("gpu_info", {})
    recent = data.get("recent_requests", {})
    scenarios = data.get("benchmark_scenarios", {})
    return (
        format_api_result(result, "Benchmark metrics loaded"),
        dataframe_from_records([gpu] if isinstance(gpu, dict) else [], ["device", "vram_gb", "vram_used_gb"]),
        dataframe_from_records(flatten_recent_requests(recent), ["service", "count", "avg_latency_ms", "avg_tokens_per_second", "avg_time_to_first_token_ms"]),
        dataframe_from_records(flatten_scenarios(scenarios), ["scenario", "seconds"]),
    )


def flatten_recent_requests(recent: Any) -> list[dict[str, Any]]:
    if not isinstance(recent, dict):
        return []
    rows = []
    for service, metrics in recent.items():
        if isinstance(metrics, dict):
            rows.append({"service": service, **metrics})
    return rows


def flatten_scenarios(scenarios: Any) -> list[dict[str, Any]]:
    if not isinstance(scenarios, dict):
        return []
    return [{"scenario": name, "seconds": value} for name, value in scenarios.items()]


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
  color: var(--fc-ink) !important;
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
  color: var(--fc-ink) !important;
}

.fc-hero-row p {
  color: var(--fc-muted) !important;
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
  color: var(--fc-ink) !important;
}

.fc-panel p {
  color: var(--fc-muted) !important;
  margin: 0;
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
  color: var(--fc-muted) !important;
}

.fc-tabs button[aria-selected="true"],
.fc-tabs button.selected {
  color: var(--fc-ink) !important;
  border-color: var(--fc-ink) !important;
}

table {
  font-size: 13px !important;
}

.gradio-container label,
.gradio-container .label-wrap span,
.gradio-container .wrap label {
  color: var(--fc-ink) !important;
}

.gradio-container input,
.gradio-container textarea {
  color: var(--fc-ink) !important;
  background: var(--fc-panel) !important;
}

.gradio-container button:not([role="tab"]) {
  color: var(--fc-ink) !important;
  background: var(--fc-panel) !important;
  border: 1px solid var(--fc-line-strong) !important;
}

.gradio-container button:not([role="tab"]):hover {
  background: var(--fc-sunk) !important;
}

.gradio-container button[aria-label="Click to upload or drop files"],
.gradio-container button[aria-label="Click to upload or drop files"] * {
  color: var(--fc-ink) !important;
  background: var(--fc-panel) !important;
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

.fc-evidence-card {
  margin-bottom: 12px;
  padding: 14px;
  border: 1px solid var(--fc-line);
  border-left: 4px solid var(--fc-primary);
  border-radius: 8px;
  background: var(--fc-panel);
}

.fc-evidence-card p {
  color: var(--fc-ink);
}

.fc-evidence-card blockquote {
  margin: 8px 0 12px;
  padding: 10px 12px;
  border-left: 3px solid var(--fc-line-strong);
  background: var(--fc-sunk);
  color: var(--fc-muted);
}
"""


if __name__ == "__main__":
    build_app().launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
