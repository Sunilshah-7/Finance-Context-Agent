# Demo Plan

`README.md` is the source of truth. The current demo is fixture-backed and
designed to show the product workflow reliably while live ingestion/retrieval is
still being built.

## Demo Thesis

Investors need to know when a company quietly changes how it describes risk.
FinContext Agent detects those changes, connects them to portfolio exposure,
and explains the impact with citations.

## Inference Thesis

The app depends on one Gateway contract. Today, the Gateway routes chat
completions to NVIDIA NIM hosted endpoints, while retrieval infrastructure,
evidence storage, citation validation, and the UI remain provider-neutral.

## Current Demo Flow

1. Open the analyst console at `http://localhost:8090`.
2. Show the seeded portfolio table.
3. Click **Analyze** to start a fixture-backed agent run.
4. Show the staged run progress:
   - Portfolio context
   - Evidence retrieval
   - Disclosure diff
   - Risk scoring
   - Memo generation
5. Show the AMD Item 1A disclosure diff.
6. Show the risk-score chart and risk-score list after the run completes.
7. Show the analyst memo with citation cards.
8. Click **Ask AMD risk question** and show the citation-backed chat answer.
9. Show the metrics panel with provider, citation pass rate, TTFT, and
   tokens/sec fixture values.

## Talking Points

- "This is a production-shaped prototype: Go Agent API, Go Gateway, Qdrant,
  SQLite, and a Next.js UI."
- "The demo is currently fixture-backed so the evidence and citations are
  deterministic for judging."
- "Citation validation is real: memo and chat citations must reference known
  evidence ids."
- "NVIDIA NIM sits behind the Gateway; the app does not couple itself directly
  to a provider SDK."
- "The next engineering step is replacing fixture evidence with live
  EDGAR-ingested chunks from SQLite and Qdrant."

## Current UI Sections

- Portfolio
- Agent run
- Disclosure diff
- Risk scores
- Analyst memo
- Chat and metrics

## Architecture Explanation

```text
Browser
  -> Agent API (Go, :8090)
    -> SQLite run/fixture metadata
    -> Qdrant collection health/setup
    -> Inference Gateway health
      -> NVIDIA NIM for chat completions
```

The root `Dockerfile` builds the Next.js UI and Go Agent API into a
HuggingFace-ready container. Compose runs Qdrant, Gateway, and Agent API as
separate services for local production-shaped testing.

## Do Not Claim Yet

- Do not say live EDGAR ingestion is wired into the current run path.
- Do not say the current Agent API performs live BM25/vector retrieval.
- Do not say chat streams tokens in the current UI.
- Do not say users can upload a portfolio in the current UI.
- Do not present buy/sell/hold recommendations.
