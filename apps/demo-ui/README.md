# apps/demo-ui

Gradio demo application deployed to HuggingFace Spaces. This is the public-facing UI for FinContext Agent.

## What this does

Provides a 7-tab Gradio interface that communicates with the Agent API over HTTPS:

| Tab | What it shows |
|-----|--------------|
| Portfolio Upload | CSV upload, holdings table display |
| Analysis | Trigger analysis job, real-time status polling |
| Disclosure Diff | Side-by-side filing section comparison with change labels |
| Risk Scores | Per-holding score table with color coding and top drivers |
| Analyst Memo | Formatted memo with clickable citation cards linking to SEC filings |
| Chat | SSE streaming citation-backed Q&A |
| Inference Metrics | Tokens/sec, latency, request volume, and provider health from the Gateway |

## Stack

- Python 3.12
- Gradio 4.x
- httpx (calls to Agent API)

## File Structure (target)

```
apps/demo-ui/
  app.py              # Main Gradio app — all tabs assembled here
  components/
    portfolio.py      # Tab 1: CSV upload + holdings table
    analysis.py       # Tab 2: analysis trigger + status polling
    diff.py           # Tab 3: disclosure diff viewer
    risk.py           # Tab 4: risk score panel
    memo.py           # Tab 5: analyst memo with citation cards
    chat.py           # Tab 6: streaming chat
    benchmark.py      # Tab 7: inference metrics panel
  api_client.py       # httpx async client for Agent API calls
  requirements.txt
  README.md           # HuggingFace Space description (shown on Space page)
```

## Running Locally

```bash
pip install -r requirements.txt

# Point to a running Agent API
AGENT_API_URL=http://localhost:8090 \
AGENT_API_KEY=your-api-key \
python app.py
# Opens at http://localhost:7860
```

## Deploying to HuggingFace Spaces

Set these secrets in your Space settings before deploying:
- `AGENT_API_URL` — the public HTTPS URL of the Agent API
- `AGENT_API_KEY` — the API key for the Agent API

```bash
# Push this directory as the Space root
git remote add space https://huggingface.co/spaces/{HF_USERNAME}/fincontext-agent
git subtree push --prefix apps/demo-ui space main
```

## Space README (YAML frontmatter required)

The `README.md` in this directory is used by HuggingFace as the Space description. It must begin with:

```yaml
---
title: FinContext Agent
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.x
app_file: app.py
pinned: false
---
```

## SSE Streaming

The chat tab uses Server-Sent Events. Gradio supports streaming via a generator function:

```python
def chat_stream(question: str, portfolio_id: str):
    with httpx.stream("POST", f"{AGENT_API_URL}/api/chat", json=...) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] == "token":
                    yield event["text"]
```

Use `gr.Textbox` with `render=False` and `gr.on(trigger, chat_stream, ..., stream=True)` in Gradio 4.x.
