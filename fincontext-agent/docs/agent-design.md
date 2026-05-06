# Agent Design

## Why 4 Agents, Not 9

The previous plan had 9 LangGraph nodes. That was reduced to 4 for these reasons:

- Each LangGraph node requires a system prompt, structured output schema, node function, state mutations, failure handling, and test coverage — approximately 6–8 hours per node
- 9 nodes × 6–8 hours = 54–72 hours of implementation, which exceeds the team's capacity for a 9-day build
- Some previously separate nodes (Portfolio Context + Retrieval Planner → combined into `portfolio_context_planner`) are logically one step
- Some previously separate nodes (Risk Scoring Agent → embedded in `analyst_memo`) produce output that only makes sense alongside the memo
- The Citation Verifier Agent is replaced by a post-processing function in the memo node (20 lines, not a full LangGraph node)
- The Compliance Guardrail Agent is replaced by a hardcoded system prompt constraint and a final disclaimer injection (always appended, not LLM-decided)

The result is 4 nodes that each do meaningful, testable work, with no nodes that exist only to coordinate other nodes.

## Agent Graph

```python
from langgraph.graph import StateGraph, END

builder = StateGraph(AnalysisState)
builder.add_node("portfolio_context_planner", portfolio_context_planner)
builder.add_node("filing_retrieval", filing_retrieval)
builder.add_node("disclosure_change", disclosure_change)
builder.add_node("analyst_memo", analyst_memo)

builder.set_entry_point("portfolio_context_planner")
builder.add_edge("portfolio_context_planner", "filing_retrieval")
builder.add_edge("filing_retrieval", "disclosure_change")
builder.add_edge("disclosure_change", "analyst_memo")
builder.add_edge("analyst_memo", END)

graph = builder.compile()
```

No conditional edges in MVP. All 4 nodes run in sequence. If a node encounters an error, it sets `state.error` and `state.partial = True` — the graph continues and returns whatever partial results are available.

## Shared State

Defined in `packages/schemas/python/state.py`. Every node takes `AnalysisState` as input and returns `AnalysisState` with its fields updated.

```python
from pydantic import BaseModel, Field
from typing import Optional

class Holding(BaseModel):
    holding_id: str
    ticker: str
    company_name: str
    cik: str
    shares: float
    market_value: float
    weight: float          # fraction of total portfolio value, 0.0–1.0
    sector: str

class RetrievalPlan(BaseModel):
    queries: list[str]                 # natural language retrieval queries
    filing_types: list[str]            # e.g. ["10-K", "10-Q"]
    sections: list[str]                # e.g. ["Item 1A", "Item 7"]
    date_range_start: str              # ISO date
    date_range_end: str                # ISO date
    comparison_pairs: list[tuple[str, str]]  # [(year_a, year_b), ...] for diff

class EvidenceChunk(BaseModel):
    chunk_id: str
    document_id: str
    ticker: str
    filing_type: str
    filed_at: str
    section: str
    text: str
    citation_anchor: str              # e.g. "AMD 10-K Item 1A paragraph 42"
    retrieval_score: float            # final reranker score
    source_url: str

class DisclosureChange(BaseModel):
    ticker: str
    section: str
    change_type: str   # new_risk | removed_risk | intensified_language | softened_language | metric_changed | legal_accounting_update
    summary: str
    old_text: str | None
    new_text: str | None
    old_citation_anchor: str | None
    new_citation_anchor: str | None
    materiality: str                  # high | medium | low
    confidence: float                 # 0.0–1.0

class RiskScore(BaseModel):
    ticker: str
    overall_score: float              # 0–100
    score_delta: float                # vs prior analysis run, 0 if first run
    confidence: float                 # 0.0–1.0
    drivers: list[dict]               # [{category, score, summary, citations}]
    portfolio_impact: dict            # {holding_weight, sector_weight, exposure_level}

class Citation(BaseModel):
    citation_id: str
    citation_anchor: str
    chunk_id: str
    document_id: str
    ticker: str

class AnalystMemo(BaseModel):
    executive_summary: str
    portfolio_exposure_affected: list[dict]   # [{ticker, weight, exposure_level}]
    top_disclosure_changes: list[dict]        # [{ticker, section, summary, citation}]
    risk_score_changes: list[dict]            # [{ticker, score, delta, top_driver}]
    evidence_table: list[Citation]
    watchlist_questions: list[str]
    limitations: str
    confidence: float
    disclaimer: str                           # hardcoded, always appended

class AnalysisState(BaseModel):
    # Always set by the caller
    user_id: str
    portfolio_id: str
    question: Optional[str] = None

    # Set by portfolio_context_planner
    holdings: list[Holding] = Field(default_factory=list)
    target_tickers: list[str] = Field(default_factory=list)
    retrieval_plan: Optional[RetrievalPlan] = None

    # Set by filing_retrieval
    retrieved_chunks: list[EvidenceChunk] = Field(default_factory=list)

    # Set by disclosure_change
    disclosure_changes: list[DisclosureChange] = Field(default_factory=list)

    # Set by analyst_memo
    risk_scores: list[RiskScore] = Field(default_factory=list)
    memo: Optional[AnalystMemo] = None
    citation_pass_rate: Optional[float] = None   # fraction of claims with verified citations

    # Error handling — set by any node on failure
    error: Optional[str] = None
    partial: bool = False
```

## Node 1: portfolio_context_planner

**File:** `services/agent-api/app/agents/portfolio_context_planner.py`

**Purpose:** Load the user's portfolio and generate a retrieval plan from the user's question or analysis request. This node is the only one that touches the SQLite database directly for portfolio data.

**Implementation steps:**

1. Query SQLite: `SELECT * FROM holdings WHERE portfolio_id = ?`
2. Compute `weight` for each holding: `market_value / sum(market_value for all holdings)`
3. Rank holdings by weight; identify `target_tickers` (all tickers, sorted by weight descending)
4. Call Qwen2.5-14B to generate a `RetrievalPlan`:
   - If `state.question` is set: build queries from the question + portfolio context
   - If `state.question` is None (general portfolio review): build queries covering recent risk factor changes, management discussion changes, and guidance changes for the top holdings

**System prompt for the planner:**
```
You are a financial research query planner. Given a user portfolio and question, generate specific retrieval queries for SEC filing search.

Portfolio: {holdings_summary}
Question: {question or "general portfolio review"}

Return a JSON object with:
- queries: 3-5 specific natural language search queries for SEC filings
- filing_types: which filing types to search (10-K, 10-Q, 8-K)
- sections: which sections to prioritize (Item 1A, Item 7, Item 7A, Item 8)
- date_range_start: earliest filing date to search (ISO format)
- date_range_end: today's date (ISO format)
- comparison_pairs: pairs of fiscal years to compare for disclosure diff

Be specific. Include financial terminology. Focus on changes and risks, not general summaries.
```

**LLM call:** Inference Gateway, `model=fincontext-planner` (routes to Qwen2.5-14B)

**Output validation:** Parse response as `RetrievalPlan`. If parsing fails, use a default plan that retrieves the latest 10-K and 10-Q for each ticker across Item 1A and Item 7.

**Error behavior:** If SQLite query fails, set `state.error = "Failed to load portfolio holdings"` and `state.partial = True`. Return state unchanged — downstream nodes check `state.holdings` before running.

## Node 2: filing_retrieval

**File:** `services/agent-api/app/agents/filing_retrieval.py`

**Purpose:** Retrieve the most relevant filing sections for the analysis. This is a pure retrieval node — it makes no LLM calls.

**Implementation steps:**

1. For each ticker in `state.target_tickers` (run in parallel with `asyncio.gather`):
   a. BM25 retrieval: query SQLite FTS5 `chunks_fts` table with each query from `retrieval_plan.queries`, filtered by `ticker` and `filing_type` and `filed_at` range. Collect top 50 candidates per query.
   b. Vector retrieval: query Qdrant `fincontext_chunks` collection with each query embedding, filtered by `ticker`, `filing_type`, `filed_at`. Collect top 50 candidates per query.

2. Merge BM25 and vector candidates using Reciprocal Rank Fusion (RRF, k=60):
```python
def rrf_merge(bm25_results, vector_results, k=60):
    scores = {}
    chunk_data = {}
    for rank, chunk in enumerate(bm25_results):
        cid = chunk.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        chunk_data[cid] = chunk
    for rank, chunk in enumerate(vector_results):
        cid = chunk.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        chunk_data[cid] = chunk
    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [chunk_data[cid] for cid in sorted_ids]
```

3. Send top 40 merged candidates to Inference Gateway `/v1/rerank`:
```json
{
  "query": "<combined query text>",
  "documents": ["<chunk text 1>", "<chunk text 2>", ...],
  "top_n": 25
}
```

4. Re-sort candidates by reranker score (descending).

5. Apply section diversity filter: for each ticker, keep at most 3 chunks per section. Then take top 12 chunks overall across all tickers combined.

6. Return `retrieved_chunks` — each chunk includes `citation_anchor`, `text`, `filing_type`, `filed_at`, `section`, `retrieval_score`, `source_url`.

**LLM calls:** None (BM25 + Qdrant vector search + BGE reranker only)

**Error behavior:** If Qdrant or SQLite returns no results for a ticker, log a warning and continue. The memo node will note missing evidence in the limitations section.

**Performance target:** Full retrieval for 5 tickers should complete in under 10 seconds on the AMD VM.

## Node 3: disclosure_change

**File:** `services/agent-api/app/agents/disclosure_change.py`

**Purpose:** Compare same-section filing content across years to detect material language drift.

**Implementation steps:**

1. Group `state.retrieved_chunks` by (ticker, section, filing_type). Sort each group by `filed_at` ascending.

2. For each (ticker, section) that has chunks from at least 2 different filing dates, create a comparison pair using the `comparison_pairs` from the retrieval plan (or the oldest vs most recent if no explicit pairs specified).

3. For each comparison pair, concatenate the chunks for each filing date into section text (old_text, new_text).

4. Normalize each section text:
   - Strip boilerplate: page numbers, EDGAR filing headers, "Table of Contents" references
   - Normalize whitespace
   - Remove XBRL tags (e.g. `<ix:nonNumeric ...>...</ix:nonNumeric>`)

5. Call Qwen2.5-14B with old_text and new_text to classify the change:

**System prompt for diff classifier:**
```
You are a financial disclosure analyst. Compare two versions of an SEC filing section and classify what changed.

Ticker: {ticker}
Section: {section}
Filing A date: {old_date}
Filing B date: {new_date}

FILING A TEXT:
{old_text}

FILING B TEXT:
{new_text}

Classify the change and return JSON with:
- change_type: one of [new_risk, removed_risk, intensified_language, softened_language, metric_changed, legal_accounting_update, boilerplate]
- summary: one sentence describing what materially changed
- materiality: high | medium | low
- confidence: 0.0 to 1.0

For "boilerplate": return this only if the change is purely formatting or legally required boilerplate with no substantive difference in meaning.
For "intensified_language": the same risk is described with stronger or more urgent language.
For "softened_language": the same risk is described with weaker or more hedged language.
Do NOT classify a change as boilerplate just because both texts discuss the same topic.
```

6. Discard all `change_type == "boilerplate"` results. They add noise to the memo.

7. For every non-boilerplate change, set `old_citation_anchor` to the citation anchor of the oldest chunk used and `new_citation_anchor` to the newest chunk used.

**LLM calls:** Qwen2.5-14B, one call per comparison pair. Run all pairs in parallel with `asyncio.gather`.

**Error behavior:** If classification fails or confidence < 0.3, skip that comparison pair with a warning. Do not include low-confidence changes in the memo.

**Risk-bearing language signals (provide as context to the classifier):** "may", "could", "materially", "adversely", "substantial", "uncertain", "depends", "concentration", "liquidity", "impairment", "going concern", "covenant", "refinancing", "single source", "investigation", "litigation", "export controls". The presence of these terms should inform materiality scoring but is not sufficient on its own to declare high materiality — the classifier must identify a substantive change in disclosure.

## Node 4: analyst_memo

**File:** `services/agent-api/app/agents/analyst_memo.py`

**Purpose:** Synthesize all evidence into a structured analyst memo with per-holding risk scores. This is the only node that uses Qwen2.5-72B.

**Implementation steps:**

**Step 1: Compute risk scores**

For each holding, compute a risk score using the formula from `docs/risk-scoring.md`:

```python
def compute_risk_score(holding: Holding, changes: list[DisclosureChange], chunks: list[EvidenceChunk]) -> RiskScore:
    # Filter to this holding's ticker
    ticker_changes = [c for c in changes if c.ticker == holding.ticker]
    ticker_chunks = [c for c in chunks if c.ticker == holding.ticker]

    # Base score from evidence severity
    severity_scores = {"high": 70, "medium": 45, "low": 20, "none": 0}
    if ticker_changes:
        max_severity = max(severity_scores.get(c.materiality, 0) for c in ticker_changes)
    else:
        max_severity = 0

    # Disclosure delta
    change_type_weights = {
        "new_risk": 1.0, "intensified_language": 0.7, "metric_changed": 0.6,
        "removed_risk": -0.3, "softened_language": -0.2, "legal_accounting_update": 0.3
    }
    disclosure_delta = sum(
        change_type_weights.get(c.change_type, 0) * severity_scores.get(c.materiality, 0)
        for c in ticker_changes
    ) / max(len(ticker_changes), 1)

    # Holding weight modifier
    weight_modifier = 1 + min(holding.weight, 0.25)

    raw_score = (max_severity * 0.35 + disclosure_delta * 0.25) * weight_modifier
    final_score = max(0.0, min(100.0, raw_score))

    return RiskScore(
        ticker=holding.ticker,
        overall_score=round(final_score, 1),
        score_delta=0.0,  # compare to previous run if available
        confidence=sum(c.confidence for c in ticker_changes) / max(len(ticker_changes), 1),
        drivers=[{"category": c.change_type, "summary": c.summary, "citation": c.new_citation_anchor} for c in ticker_changes[:3]],
        portfolio_impact={
            "holding_weight": round(holding.weight, 3),
            "exposure_level": "high" if holding.weight > 0.20 else "medium" if holding.weight > 0.10 else "low"
        }
    )
```

**Step 2: Generate memo with Qwen2.5-72B**

Build the prompt:
```
You are a senior financial analyst. Write a portfolio impact memo based on the evidence below.

PORTFOLIO:
{holdings_table}

DISCLOSURE CHANGES DETECTED:
{formatted_changes}

EVIDENCE CHUNKS (cite these using [chunk_id]):
{formatted_chunks}

Write a structured memo with exactly these sections:
1. Executive Summary (2-3 sentences)
2. Portfolio Exposure Affected (table)
3. Top Disclosure Changes (one paragraph per change, cite the relevant chunk with [chunk_id])
4. Risk Score Changes (table)
5. Evidence Table (list all citations used)
6. Watchlist Questions (3-5 questions for the next earnings call)
7. Limitations and Confidence

Rules:
- Every factual claim must be followed by [chunk_id] referencing a chunk from the Evidence Chunks list
- Do NOT include buy, sell, hold, or short recommendations
- Use hedged language: "may indicate", "suggests", "warrants monitoring"
- If evidence is insufficient, say so explicitly rather than speculating
```

**Step 3: Citation post-processing**

After the memo is generated:
```python
def verify_citations(memo_text: str, retrieved_chunks: list[EvidenceChunk]) -> tuple[str, float]:
    valid_ids = {c.chunk_id for c in retrieved_chunks}
    pattern = r'\[([a-z0-9_-]+)\]'
    found_ids = re.findall(pattern, memo_text)
    
    verified = 0
    removed_sentences = 0
    
    for sentence in split_into_sentences(memo_text):
        sentence_ids = re.findall(pattern, sentence)
        if sentence_ids:
            if all(cid in valid_ids for cid in sentence_ids):
                verified += len(sentence_ids)
            else:
                # Remove sentence with invalid citation
                memo_text = memo_text.replace(sentence, "")
                removed_sentences += 1
    
    pass_rate = verified / max(len(found_ids), 1)
    return memo_text, pass_rate
```

**Step 4: Append hardcoded disclaimer**

Always append — this is not LLM-generated:
```
---
This memo is produced by an automated financial intelligence system for research purposes only. 
It does not constitute investment advice, a recommendation to buy or sell any security, or a 
solicitation to make any investment. Past performance of disclosed risk factors does not 
predict future price performance. Consult a qualified financial advisor before making 
investment decisions. Citations reference publicly available SEC filings available at sec.gov.
```

**LLM calls:** Qwen2.5-72B, one call for memo generation (this is the expensive call).

**Error behavior:** If 72B call fails or times out after 120 seconds, fall back to Qwen2.5-14B for a shorter summary. Set `state.partial = True`.

## Prompting Pattern

All intermediate nodes (portfolio_context_planner, disclosure_change) use strict structured JSON output. Tell the model to return only valid JSON with no markdown wrapping:

```
Return only a valid JSON object. Do not include markdown code fences, commentary, or explanation. Begin your response with `{` and end with `}`.
```

Parse with `model.model_validate_json(response_text)` — if parsing fails, the node logs the raw response and uses a fallback.

Only the `analyst_memo` node generates prose. Even there, the memo sections follow a fixed template that the model fills in.

## Testing Each Node

Each node must be testable in isolation without a running vLLM instance:

```python
# tests/test_nodes.py
from unittest.mock import patch, AsyncMock

async def test_portfolio_context_planner():
    state = AnalysisState(user_id="u1", portfolio_id="p1", question="What are supply chain risks?")
    
    with patch("app.agents.portfolio_context_planner.get_holdings") as mock_holdings:
        mock_holdings.return_value = [Holding(ticker="AMD", weight=0.25, ...)]
    
    with patch("app.clients.inference_gateway.chat_completion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"queries": ["supply chain risks AMD"], "filing_types": ["10-K"], ...}'
        
        result = await portfolio_context_planner(state)
        
        assert result.target_tickers == ["AMD"]
        assert result.retrieval_plan is not None
        assert len(result.retrieval_plan.queries) > 0
```

Every node test mocks the Inference Gateway HTTP client and the SQLite/Qdrant calls. Integration tests (in `tests/integration/`) use a real local Qdrant and a real SQLite with seed data from `demo/seed_portfolio.csv`.
