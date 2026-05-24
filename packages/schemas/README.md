# packages/schemas

Shared data contracts used by all Python services. Every Pydantic model that crosses service boundaries lives here.

<<<<<<< HEAD
**TypeScript types are not generated for this project.** The React frontend (HuggingFace Static Space) consumes the Agent API HTTP endpoints directly; only Python services import these schemas.
=======
The Python services share these Pydantic schemas directly. The React frontend should consume the Agent API contracts rather than importing Python schema code.
>>>>>>> origin/dev

## What lives here

```
packages/schemas/
  python/
    __init__.py
    state.py      # AnalysisState and all LangGraph node subtypes — the central contract
    db.py         # SQLite row types plus Qdrant chunk payload contract
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
- `QdrantChunkPayload` — vector-store payload contract for `fincontext_chunks`

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
