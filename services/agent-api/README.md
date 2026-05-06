# services/agent-api

FastAPI service that runs the multi-agent financial analysis workflow on AMD Developer Cloud.

## Build Responsibilities

- LangGraph orchestration.
- Portfolio context loading.
- Retrieval planning.
- Disclosure diffing.
- Risk scoring.
- Analyst memo generation.
- Citation verification.
- Compliance guardrails.

## Suggested Stack

- Python 3.12.
- FastAPI.
- LangGraph.
- LlamaIndex.
- Pydantic.
- httpx.
- OpenTelemetry.

## Key Files

```text
app/
  main.py
  graph.py
  agents/
    portfolio_context.py
    retrieval_planner.py
    filing_retrieval.py
    disclosure_change.py
    metric_table.py
    risk_scoring.py
    analyst_memo.py
    citation_verifier.py
    compliance_guardrail.py
  clients/
    vllm.py
    embeddings.py
    reranker.py
    r2.py
  models/
    state.py
    schemas.py
```

