# Demo Plan

## Demo Thesis

"Investors need to know when a company quietly changes how it describes risk. FinContext Agent detects those changes automatically, connects them to your actual portfolio exposure, and explains the impact with citations you can verify."

The demo is NOT about fancy AI tricks. It's about solving a real financial analyst problem that takes hours to do manually, in under 90 seconds, with verifiable sources.

## Inference Thesis (tell this to judges explicitly)

The live MVP uses NVIDIA NIM hosted inference behind a provider-agnostic Inference Gateway. The Agent API and ingestion worker do not call NIM directly; they call the Gateway.

Say this out loud during the demo: "The agent workflow is isolated from the inference provider. Today the Gateway routes chat completions to NVIDIA NIM, while retrieval, evidence storage, citation verification, and the UI stay unchanged."

## Seed Portfolio

File: `demo/seed_portfolio.csv`

```csv
ticker,shares,market_value,sector
AMD,100,15000,Semiconductors
MSFT,40,17000,Software
JPM,50,10000,Financials
TSLA,30,7500,Consumer Discretionary
XOM,80,9500,Energy
```

**Why these tickers:**
- AMD: AMD judges see their own company analyzed, impressive on multiple levels
- NVDA: Direct AMD competitor, interesting cross-company comparison in semiconductor risk
- MSFT: Large-cap tech, diverse risk profile vs semiconductors
- JPM: Financials for cross-sector balance, good liquidity risk signals
- TSLA: High disclosure volatility, best for the diff demo (they change language frequently)

Pre-ingest all 5 tickers before demo day. The demo never shows live ingestion.

## Demo Flow (9 steps, ~90 seconds total)

### Step 1: Upload Portfolio (15 seconds)

"I'm uploading a sample portfolio with five holdings across semiconductors, software, financials, energy, and consumer discretionary."

- Drag and drop `demo/seed_portfolio.csv` into the React Portfolio Upload tab
- Show the holdings table that appears: ticker, shares, market value, weight, sector
- Point out AMD is the largest semiconductor holding at 25.4% weight

### Step 2: Trigger Analysis (5 seconds)

"I'll ask: what changed in risk disclosures for my semiconductor holdings?"

- Type the question: "What changed in supply-chain and customer concentration risk for my semiconductor holdings?"
- Click "Analyze"
- Show the progress stage updating: Planning → Retrieving → Analyzing → Writing

### Step 3: Show Disclosure Diff (25 seconds)

*This is the hero moment. Do not rush it.*

Navigate to the Disclosure Diff tab. Select AMD, Item 1A, 2022 vs 2025.

"In 2022, AMD wrote: 'We source certain components from a limited number of suppliers.' In 2025, that same section now reads: 'We have a significant concentration of supply chain dependency on certain third-party manufacturers, particularly for advanced process nodes.' That's not the same sentence. FinContext Agent classified this as an intensified language change with high materiality, traced it to paragraph 42 of the 2025 10-K, and connected it to the 25% AMD holding in this portfolio."

- Show side-by-side diff with highlighted changes
- Show the materiality badge: HIGH | Intensified Language
- Click the citation card to show it links to the actual EDGAR filing URL

### Step 4: Show New Risk in AMD 2025 10-K (15 seconds)

"There's also a completely new risk disclosure in 2025 that didn't exist in prior filings."

- Show the "new_risk" classification for the export controls paragraph
- Citation: `AMD 10-K Item 1A paragraph 18`
- Old text: null (not in prior filing)
- New text: "The U.S. government has implemented export restrictions on advanced AI accelerators..."

"This paragraph did not exist in the 2022, 2023, or 2024 10-K. It appeared in 2025 for the first time. That's a material new risk for anyone holding AMD stock."

### Step 5: Show Analyst Memo (20 seconds)

Navigate to the Analyst Memo tab.

"Here's the generated memo. Every claim has a citation."

- Show the executive summary: 2-3 sentences about semiconductor portfolio risk
- Show the top disclosure changes table: AMD supply chain, AMD export controls, NVDA supply chain
- Point to an inline `[AMD 10-K Item 1A paragraph 42]` citation in a paragraph
- Click the citation card — show it opens to the real EDGAR URL
- Scroll to the evidence table at the bottom
- Show the investment disclaimer at the bottom

"The system generated this with citation pass rate 0.94 — 94% of claims are traceable to specific filing paragraphs."

### Step 6: Show Risk Score (10 seconds)

Navigate to the Risk Scores tab.

"AMD: risk score 58 out of 100, up 12 points from the prior analysis. The top driver is supply chain concentration risk. NVDA: 62, also semiconductor supply chain. JPM and XOM are below 25 — different risk profile entirely."

Show the color-coded score table.

### Step 7: Chat Q&A (15 seconds)

Navigate to the Chat tab.

"Watch the citations appear in real time."

- Type: "Why is AMD's supply chain risk higher this year?"
- Show tokens streaming in the chat interface
- Watch citation cards appear below the answer as it completes

### Step 8: Inference Metrics Panel (15 seconds)

Navigate to the Inference Metrics tab.

"Here are the performance numbers from the last analysis."

Show:
- Tokens per second for Qwen2.5-72B: ~50 tokens/sec
- Time to first token: ~380ms
- Provider: NVIDIA NIM
- Full 5-stock portfolio analysis: 91 seconds end-to-end

"The app sees a stable OpenAI-compatible Gateway contract. The Gateway handles provider routing, request IDs, latency metrics, retries, and error normalization."

### Step 9: Architecture Slide (30 seconds — verbal only)

"Three layers. HuggingFace Spaces for the public UI — that's this React interface. The backend host runs the Agent API, Gateway, Qdrant, and SQLite. NVIDIA NIM provides hosted LLM inference. SEC EDGAR is the data source — all public filings, no data license required."

"The key engineering choice is that all model calls go through the Inference Gateway, so the workflow stays stable even when the serving backend changes."

---

## Demo Screens (React Tabs)

### Tab 1: Portfolio Upload
- CSV file input widget
- Holdings table: ticker, shares, market_value, weight %, sector
- Status line: "5 holdings loaded. All tickers resolved to CIK."

### Tab 2: Analysis
- Question text input
- "Analyze" button
- Progress status box (updates every 2 seconds): stage name + elapsed time
- When complete: "Analysis complete in 91s | 12 findings | citation pass rate 94%"

### Tab 3: Disclosure Diff
- Dropdown: select ticker (AMD, NVDA, MSFT, JPM, TSLA)
- Dropdown: select section (Item 1A, Item 7, Item 7A)
- Slider or dropdown: select year_a and year_b (2022–2025)
- Side-by-side text panels:
  - Left: old filing section with deleted text highlighted in red
  - Right: new filing section with added text highlighted in green
- Change cards below the diff: one card per classified change with materiality badge and citation

### Tab 4: Risk Scores
- Table: ticker | score (0-100) | delta | exposure level | top driver
- Color coding: green (0-20), yellow (21-40), orange (41-60), red (61-80), dark red (81-100)
- Bar chart: portfolio-level risk composition by category

### Tab 5: Analyst Memo
- Formatted markdown memo with inline citation references `[AMD 10-K Item 1A paragraph 42]`
- Each citation renders as a clickable card showing: section, filing date, chunk text excerpt, link to SEC EDGAR URL
- Sections: Executive Summary, Portfolio Exposure, Top Changes, Risk Scores, Evidence Table, Watchlist Questions, Limitations, Disclaimer

### Tab 6: Chat
- Text input: "Ask a question about your portfolio..."
- "Send" button
- Chat history with SSE streaming (tokens appear one by one)
- Citation cards appear below each answer when streaming completes

### Tab 7: Inference Metrics
- Gauge: tokens per second (Qwen2.5-72B and Qwen2.5-14B)
- Gauge: request latency
- Table: benchmark scenario | latency | tokens in | tokens out
- Note: "LLM inference via the Gateway · local retrieval and citation metrics"

---

## Judge-Facing Talking Points

| What judges care about | What we say |
|----------------------|-------------|
| Inference architecture | "NVIDIA NIM hosted inference behind an OpenAI-compatible Gateway. Benchmark panel shows real request metrics." |
| HuggingFace integration | "Qwen and BGE pulled from HF Hub. Demo UI is a public HuggingFace Space." |
| Agentic workflow | "4 LangGraph agents with typed shared state. Portfolio context → retrieval → disclosure diff → memo." |
| Real-world usefulness | "SEC EDGAR data, real filings, real citations, links to actual SEC documents." |
| Differentiation | "The disclosure diff is the feature that doesn't exist anywhere else. We detect language drift across years." |
| Code quality | "Python, FastAPI, LangGraph, Pydantic throughout. Pre-ingested data. Clean architecture." |

---

## Build-in-Public Post Schedule

| When | Post topic | Platform |
|------|-----------|----------|
| Day 7 (May 17) | Swapping the inference backend to NVIDIA NIM without changing the agent graph | X and LinkedIn |
| Day 8 (May 18) | BM25 + vector hybrid retrieval on financial text — real precision numbers | X and LinkedIn |
| Day 9 (May 19) | Hosted 72B inference with NVIDIA NIM plus local citation-grounded retrieval | X and LinkedIn |

Tag every post: `#AMDDevHackathon` `#HuggingFace` `#LangGraph` `#NVIDIA`

These posts qualify for the Build-in-Public prize pool AND make the submission visible to judges before they open it.

---

## What Can Go Wrong and Fallbacks

| Risk | Probability | Fallback |
|------|-------------|----------|
| Backend unreachable during demo | Low | Record demo video on Day 8, show video |
| HuggingFace Space can't reach backend | Medium | ngrok tunnel as fallback, test this before demo |
| NIM endpoint unavailable or rate-limited | Medium | Fall back to smaller hosted model for memo generation, note it in demo |
| EDGAR parsing gave bad results for a ticker | Low | Pre-demo manual check, remove problematic ticker from seed portfolio |
| Hosted model generates citation hallucination | Medium | Citation post-processor strips them, mention this in demo as a feature |
| Analysis takes > 3 minutes | Low | Pre-run analysis and show results rather than live run |
