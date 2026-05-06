# Demo Plan

## Demo Story

"An investor uploads a portfolio. Overnight, a new 10-Q arrives for one holding. FinContext Agent detects disclosure changes, links them to portfolio exposure, updates the holding risk score, and generates a citation-backed memo."

## Seed Portfolio

Use 5-8 recognizable tickers across sectors. For an AMD hackathon, include AMD as one holding.

Example CSV:

```csv
ticker,shares,market_value,sector
AMD,100,15000,Semiconductors
MSFT,40,17000,Software
JPM,50,10000,Financials
TSLA,30,7500,Consumer Discretionary
XOM,80,9500,Energy
```

## Demo Screens

1. Dashboard:
   - total portfolio value.
   - sector weights.
   - top risk increases.
   - latest analyzed filings.

2. Filing explorer:
   - document list.
   - parsed sections.
   - citation anchors.

3. Disclosure diff:
   - old vs new wording.
   - highlighted changes.
   - materiality labels.

4. Risk panel:
   - per-holding score.
   - category breakdown.
   - score delta.

5. Analyst memo:
   - executive summary.
   - exposure impact.
   - evidence table.
   - follow-up questions.

6. AMD GPU benchmark:
   - tokens/sec.
   - filings processed.
   - concurrent agent calls.
   - latency chart.

## Script

1. Upload seed portfolio.
2. Start "Analyze latest filings".
3. Show job status streaming through Cloudflare.
4. Open AMD holding.
5. Show latest vs previous risk disclosure diff.
6. Ask: "What changed in supply-chain or customer concentration risk, and how does it affect my portfolio?"
7. Show answer with citations.
8. Open benchmark panel showing AMD GPU inference metrics.
9. Close with architecture: Cloudflare for app/edge, AMD Developer Cloud for large-context inference, Hugging Face for models.

## Judge-Facing Highlights

- Clear agentic workflow with specialized agents and verifier loop.
- Real financial documents, not toy prompts.
- Portfolio-aware outputs instead of generic filing summaries.
- Citation-backed claims.
- AMD GPUs used for the hardest workload.
- Cloudflare deployment gives a polished public demo.

