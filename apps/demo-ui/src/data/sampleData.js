/**
 * Clearly labeled sample data used when Agent API is unavailable.
 *
 * Values are illustrative UI fixtures, not live market data, investment advice,
 * or measured NIM/Gateway inference metrics.
 */

export const SAMPLE_PORTFOLIO = {
  id: "sample-portfolio",
  name: "Demo Portfolio",
  sourceLabel: "Sample data",
  holdings: [
    { ticker: "AMD", name: "Advanced Micro Devices", shares: 100, marketValue: 15000, sector: "Semiconductors", weight: 0.245 },
    { ticker: "NVDA", name: "NVIDIA Corporation", shares: 15, marketValue: 9500, sector: "Semiconductors", weight: 0.155 },
    { ticker: "MSFT", name: "Microsoft Corporation", shares: 40, marketValue: 17000, sector: "Software", weight: 0.278 },
    { ticker: "JPM", name: "JPMorgan Chase", shares: 50, marketValue: 10000, sector: "Financials", weight: 0.163 },
    { ticker: "TSLA", name: "Tesla", shares: 30, marketValue: 7500, sector: "Consumer Discretionary", weight: 0.123 },
  ],
};

export const SAMPLE_DRIFT = [
  {
    id: "drift-amd-export",
    ticker: "AMD",
    section: "Item 1A",
    topic: "Export controls",
    changeType: "intensified_language",
    severity: "high",
    confidence: 0.91,
    oldCitation: "AMD 10-K Item 1A paragraph 42",
    newCitation: "AMD 10-K Item 1A paragraph 44",
    oldText: "Prior filing language described export controls as a possible future limitation on advanced processor sales.",
    newText: "Current filing language describes export controls as a material limitation that may affect data center revenue and customer access.",
    summary: "Export-control risk shifted from hypothetical language to realized and continuing impact language.",
  },
  {
    id: "drift-amd-supply",
    ticker: "AMD",
    section: "Item 7",
    topic: "Advanced packaging supply",
    changeType: "new_risk",
    severity: "high",
    confidence: 0.86,
    oldCitation: "AMD 10-K Item 7 paragraph 58",
    newCitation: "AMD 10-K Item 7 paragraph 63",
    oldText: "Prior filing language discussed supplier dependence in general terms.",
    newText: "Current filing language adds a specific constraint around advanced packaging capacity and product ramp timing.",
    summary: "New supply-chain language creates a stronger bridge between filing evidence and semiconductor portfolio risk.",
  },
  {
    id: "drift-msft-capex",
    ticker: "MSFT",
    section: "Item 7",
    topic: "AI infrastructure capital expenditure",
    changeType: "metric_changed",
    severity: "medium",
    confidence: 0.79,
    oldCitation: "MSFT 10-Q Item 2 paragraph 22",
    newCitation: "MSFT 10-Q Item 2 paragraph 24",
    oldText: "Earlier disclosure described AI infrastructure spending as elevated but manageable.",
    newText: "Current disclosure ties higher infrastructure spending to GPU supply and data center deployment timing.",
    summary: "Capex discussion changed from broad investment language to a dependency on external hardware supply.",
  },
];

export const SAMPLE_EVIDENCE = [
  {
    chunkId: "sample-amd-1a-44",
    ticker: "AMD",
    filingType: "10-K",
    filedAt: "2026-02-21",
    section: "Item 1A",
    citationAnchor: "AMD 10-K Item 1A paragraph 44",
    sourceUrl: "https://www.sec.gov/",
    preview: "Export control restrictions on advanced processor products may materially affect data center revenue, customer relationships, and market access in restricted jurisdictions.",
  },
  {
    chunkId: "sample-amd-7-63",
    ticker: "AMD",
    filingType: "10-K",
    filedAt: "2026-02-21",
    section: "Item 7",
    citationAnchor: "AMD 10-K Item 7 paragraph 63",
    sourceUrl: "https://www.sec.gov/",
    preview: "Advanced packaging capacity and foundry allocation may constrain the timing and mix of data center accelerator shipments.",
  },
  {
    chunkId: "sample-msft-7-24",
    ticker: "MSFT",
    filingType: "10-Q",
    filedAt: "2026-04-24",
    section: "Item 7",
    citationAnchor: "MSFT 10-Q Item 7 paragraph 24",
    sourceUrl: "https://www.sec.gov/",
    preview: "AI infrastructure deployment depends on third-party GPU supply and data center capacity availability.",
  },
];

export const SAMPLE_RISK = [
  {
    ticker: "AMD",
    score: 72,
    delta: 14,
    confidence: 0.88,
    drivers: ["Export controls", "Packaging capacity", "Customer concentration"],
    impact: "Largest evidence concentration in semiconductor holdings.",
    citations: ["AMD 10-K Item 1A paragraph 44", "AMD 10-K Item 7 paragraph 63"],
  },
  {
    ticker: "NVDA",
    score: 78,
    delta: 9,
    confidence: 0.84,
    drivers: ["Export controls", "Inventory exposure"],
    impact: "Peer evidence helps compare semiconductor risk language.",
    citations: ["NVDA 10-Q Item 1A paragraph 7"],
  },
  {
    ticker: "MSFT",
    score: 48,
    delta: 6,
    confidence: 0.76,
    drivers: ["AI capex", "GPU supply"],
    impact: "Software holding has infrastructure dependency language.",
    citations: ["MSFT 10-Q Item 7 paragraph 24"],
  },
];

export const SAMPLE_MEMO = {
  sourceLabel: "Sample memo",
  executiveSummary:
    "Sample output: semiconductor exposure shows elevated disclosure drift around export controls, packaging capacity, and AI infrastructure dependencies. The strongest sample evidence is concentrated in AMD Item 1A and Item 7 language.",
  affectedHoldings: ["AMD", "NVDA", "MSFT"],
  watchlistQuestions: [
    "What changed in export-control exposure language across the latest semiconductor filings?",
    "Which supplier or packaging constraints are now stated more directly than in prior filings?",
    "Which citations should analysts inspect before writing a portfolio memo?",
  ],
  disclaimer:
    "This output is research assistance only and does not constitute investment advice.",
};

export const SAMPLE_BENCHMARK = {
  sourceLabel: "Sample inference placeholders",
  status: "Unavailable until backend metrics are connected",
  metrics: [
    { label: "Reasoner tokens/sec", value: "Unavailable", note: "Requires live Gateway metrics" },
    { label: "Time to first token", value: "Unavailable", note: "Requires live Gateway metrics" },
    { label: "Provider status", value: "Unavailable", note: "Requires live NIM/Gateway health" },
    { label: "Embedding latency", value: "Unavailable", note: "Requires Gateway metrics" },
  ],
};
