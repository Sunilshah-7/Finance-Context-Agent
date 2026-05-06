# Agent Design

## Agent Graph

Use LangGraph because the workflow needs typed state, branching, retries, and verifier loops.

```text
Start
  -> Portfolio Context Agent
  -> Retrieval Planner
  -> Filing Retrieval Agent
  -> Disclosure Change Agent
  -> Metric/Table Agent
  -> Risk Scoring Agent
  -> Analyst Memo Agent
  -> Citation Verifier Agent
  -> Compliance Guardrail Agent
  -> Final Response
```

## Shared State

```python
class AnalysisState(BaseModel):
    user_id: str
    portfolio_id: str
    question: str | None
    holdings: list[Holding]
    target_tickers: list[str]
    retrieved_chunks: list[EvidenceChunk]
    disclosure_changes: list[DisclosureChange]
    table_metrics: list[FinancialMetric]
    risk_scores: list[RiskScore]
    memo: AnalystMemo | None
    citation_errors: list[CitationError]
    compliance_flags: list[str]
```

## Agents

### Portfolio Context Agent

Purpose:

- Load holdings.
- Compute weights and sector exposure.
- Identify top affected holdings.
- Expand tickers to peers and supply-chain terms when relevant.

Outputs:

- portfolio summary.
- exposure map.
- target ticker list.
- retrieval filters.

### Retrieval Planner

Purpose:

- Turn a user question or portfolio review request into specific retrieval queries.
- Choose filing types, sections, and time windows.

Example queries:

- "liquidity and debt obligations changes latest 10-Q vs prior 10-Q".
- "risk factor customer concentration semiconductor demand".
- "management discussion margin pressure inventory impairment".

### Filing Retrieval Agent

Purpose:

- Run hybrid retrieval.
- Rerank evidence.
- Return citation-ready chunks.

Guardrail:

- It cannot generate final claims. It only returns evidence.

### Disclosure Change Agent

Purpose:

- Compare latest and prior filing sections.
- Identify material wording and numeric changes.
- Separate boilerplate from substantive changes.

Outputs:

- change summary.
- old citation.
- new citation.
- materiality label.
- confidence.

### Metric/Table Agent

Purpose:

- Extract revenue, gross margin, operating income, cash, debt, segment data, and guidance metrics.
- Compare values over time.
- Flag metric-document inconsistencies.

MVP can use parsed HTML/XBRL tables. Track 3 extension can add PDF/table vision.

### Risk Scoring Agent

Purpose:

- Convert evidence and portfolio exposure into risk categories and 0-100 scores.
- Explain score deltas.

Guardrail:

- Must cite every driver.
- Must include confidence.
- Must avoid trading instructions.

### Analyst Memo Agent

Purpose:

- Produce readable analyst-style memo.
- Explain portfolio impact.
- Include citations and follow-up questions.

### Citation Verifier Agent

Purpose:

- Check every claim-citation pair.
- Remove unsupported claims.
- Ask upstream agents to retrieve more evidence when necessary.

### Compliance Guardrail Agent

Purpose:

- Add investment-research disclaimer.
- Block personalized recommendations such as "buy", "sell", or "short".
- Flag missing uncertainty, missing citations, and unverifiable claims.

## Prompting Pattern

Use strict structured outputs for all intermediate agents. Reserve prose generation for the final memo.

For citation-backed claims:

```text
Claim:
Evidence:
Ticker:
Document:
Filing date:
Citation anchor:
Confidence:
```

## Failure Handling

- Missing filing: return a partial analysis with explicit missing data.
- Retrieval low confidence: ask retrieval planner for expanded query.
- Citation failed: remove or downgrade the claim.
- Model timeout: return top findings and continue job asynchronously.

