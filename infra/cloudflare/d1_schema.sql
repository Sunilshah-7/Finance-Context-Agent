CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolios (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  base_currency TEXT NOT NULL DEFAULT 'USD',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS holdings (
  id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  company_name TEXT,
  cik TEXT,
  shares REAL,
  market_value REAL,
  cost_basis REAL,
  sector TEXT,
  weight REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  ticker TEXT NOT NULL,
  cik TEXT,
  filing_type TEXT NOT NULL,
  accession_number TEXT,
  filed_at TEXT,
  source_url TEXT,
  r2_key TEXT NOT NULL,
  parsed_r2_key TEXT,
  checksum TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  section TEXT,
  item_label TEXT,
  chunk_index INTEGER NOT NULL,
  text_hash TEXT NOT NULL,
  citation_anchor TEXT NOT NULL,
  token_count INTEGER,
  vector_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
  id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  completed_at TEXT,
  error TEXT,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  holding_id TEXT,
  severity TEXT NOT NULL,
  risk_category TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  score_delta REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
  FOREIGN KEY (holding_id) REFERENCES holdings(id)
);

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_documents_ticker ON documents(ticker);
CREATE INDEX IF NOT EXISTS idx_documents_filing_date ON documents(filing_type, filed_at);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_jobs_portfolio ON analysis_jobs(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_findings_portfolio ON findings(portfolio_id);

