export type Holding = {
  ticker: string;
  company: string;
  shares: number;
  market_value: number;
  weight: number;
  sector: string;
};

export type PortfolioItem = Holding & {
  risk_score?: number;
  risk_delta?: number;
  drift_state: 'up' | 'flat' | 'down';
};

export type Portfolio = {
  id: string;
  name: string;
  total_value: number;
  holdings: Holding[];
  disclaimer: string;
};

export type EvidenceCitation = {
  id: string;
  ticker: string;
  anchor: string;
  filing_type: string;
  year: number;
  section: string;
  excerpt: string;
  source_url: string;
};

export type DisclosureChange = {
  id: string;
  ticker: string;
  section: string;
  from_year: number;
  to_year: number;
  change_type: string;
  materiality: string;
  confidence: number;
  summary: string;
  old_text: string;
  new_text: string;
  citation_ids: string[];
};

export type DiffBlock = DisclosureChange & {
  risk_label: string;
  changed_phrases: string[];
};

export type RiskDriver = {
  category: string;
  score: number;
  summary: string;
  citation_ids: string[];
};

export type RiskScore = {
  ticker: string;
  score: number;
  delta: number;
  exposure_level: string;
  weight: number;
  top_driver: string;
  drivers: RiskDriver[];
};

export type RiskMetric = RiskScore & {
  confidence: number;
};

export type LogEvent = {
  id: string;
  stage_id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'ok';
  message: string;
};

export type AnalystMemo = {
  executive_summary: string;
  exposure_affected: Holding[];
  top_changes: Array<{ ticker: string; section: string; summary: string; citation_ids: string[] }>;
  risk_scores: RiskScore[];
  watchlist: string[];
  limitations: string;
  confidence: number;
  citation_ids: string[];
  disclaimer: string;
};

export type AgentStage = {
  id: string;
  label: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  summary?: string;
};

export type Metrics = {
  provider: string;
  planner_latency_ms: number;
  memo_latency_ms: number;
  time_to_first_token_ms: number;
  tokens_per_second: number;
  citation_pass_rate: number;
  last_portfolio_analysis: string;
};

export type AgentRun = {
  id: string;
  status: string;
  question: string;
  stages: AgentStage[];
  portfolio: Portfolio;
  retrieved_evidence: EvidenceCitation[];
  disclosure_changes: DisclosureChange[];
  risk_scores: RiskScore[];
  memo?: AnalystMemo;
  metrics: Metrics;
};

export type ChatAnswer = {
  answer: string;
  citations: EvidenceCitation[];
  disclaimer: string;
};

export type DemoRiskScoresResponse = {
  risk_scores: RiskScore[];
};

export type DemoEvidenceResponse = {
  evidence: EvidenceCitation[];
};
