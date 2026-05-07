---
title: FinContext Agent
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
---

# FinContext Agent

FinContext Agent is a citation-grounded financial intelligence demo built for the AMD Developer Hackathon 2026. It analyzes pre-ingested SEC filings for a portfolio, identifies disclosure language drift across 10-K and 10-Q filings, and produces analyst-style memos tied to exact filing citations.

## Why AMD hardware matters

The demo is designed around AMD Instinct GPU capacity on AMD Developer Cloud. A single MI300X provides 192 GB of HBM3 VRAM, which is enough to run a 70B-class model in FP16 without multi-GPU tensor parallel orchestration. That lets the project keep long annual-report context in one model session for the judge-facing memo workflow.

## Tabs in this Space

- `Portfolio Upload` imports a CSV portfolio into the Agent API.
- `Analysis` starts a portfolio analysis job and polls progress.
- `Filing Explorer` lists ingested filings by ticker.
- `Disclosure Diff` surfaces cross-filing disclosure changes.
- `Risk Scores` shows per-holding risk outputs.
- `Analyst Memo` renders the memo and evidence table.
- `Chat` streams citation-backed responses from the Agent API.
- `AMD Benchmark` shows gateway and GPU benchmark metrics.

## Required secrets

Set these HuggingFace Space secrets before deployment:

- `AGENT_API_URL`
- `AGENT_API_KEY`
