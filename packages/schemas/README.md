# packages/schemas

Shared data contracts used by all Python services. Every Pydantic model that crosses service boundaries lives here.

**TypeScript types are not generated for this project.** The frontend is Gradio (Python), so all services share the Python schemas directly.

## What lives here

```
packages/schemas/
  python/
    __init__.py
    state.py      # AnalysisState and all LangGraph node subtypes — the central contract
    db.py         # SQLite row types: Portfolio, Holding, Document, Chunk, AnalysisJob, Finding
    api.py        # FastAPI request/response models for Agent API endpoints
```

## state.py — The Central Contract

`AnalysisState` is the LangGraph shared state type. Every agent node takes `AnalysisState` as input and returns `AnalysisState` with its fields updated. Changing this file affects all 4 agent nodes.

See `docs/agent-design.md` for the full schema definition.

Core types:
- `AnalysisState` — top-level LangGraph state
- `Holding` — a portfolio position
- `RetrievalPlan` — output of portfolio_context_planner, input to filing_retrieval
- `EvidenceChunk` — a retrieved chunk with citation anchor, used by disclosure_change and analyst_memo
- `DisclosureChange` — a classified change between two filing versions
- `RiskScore` — computed risk score per holding
- `AnalystMemo` — the final structured memo

## Rules

- Never define schema types inline in service code — always import from this package
- Add a type here first, then add the field that uses it
- All fields must have type annotations
- Optional fields must have a default (`Optional[X] = None` or `list[X] = Field(default_factory=list)`)
- Do not add service-specific logic here — only data definitions

## Installing in a service

```bash
# From a service directory (e.g., services/agent-api/)
pip install -e ../../packages/schemas
```

Or add to `requirements.txt`:
```
-e ../../packages/schemas
```
