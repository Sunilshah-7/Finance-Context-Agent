-- FinContext Agent SQLite Schema
-- Apply with: sqlite3 fincontext.db < infra/schema.sql
-- Enable WAL mode for concurrent reads during analysis
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Core tables

CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS holdings (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    cik TEXT,
    shares REAL,
    market_value REAL NOT NULL,
    cost_basis REAL,
    sector TEXT,
    weight REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    cik TEXT,
    company_name TEXT,
    filing_type TEXT NOT NULL,
    accession_number TEXT,
    filed_at TEXT,
    fiscal_period TEXT,
    source_url TEXT,
    local_path TEXT,
    sections_parsed TEXT,  -- JSON array of section labels
    checksum TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,       -- UUID, matches Qdrant point ID
    document_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    filed_at TEXT NOT NULL,
    section TEXT NOT NULL,     -- e.g. "item_1a"
    item_label TEXT,           -- e.g. "Item 1A"
    section_title TEXT,        -- e.g. "Risk Factors"
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,        -- full chunk text (also stored in Qdrant payload)
    text_hash TEXT NOT NULL,   -- SHA256[:16] for deduplication
    token_count INTEGER,
    citation_anchor TEXT NOT NULL,  -- e.g. "AMD 10-K Item 1A paragraph 42"
    source_url TEXT,
    is_table INTEGER NOT NULL DEFAULT 0,  -- 1 if this chunk is a table
    vector_id TEXT,            -- Qdrant point ID (same as id for consistency)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    job_type TEXT NOT NULL,    -- "portfolio_review" | "custom_question" | "latest_filings"
    status TEXT NOT NULL DEFAULT 'queued',  -- queued | running | completed | failed
    stage TEXT,                -- planning | retrieving | analyzing | writing | complete
    progress REAL DEFAULT 0.0, -- 0.0 to 1.0
    question TEXT,
    citation_pass_rate REAL,
    findings_count INTEGER,
    error TEXT,
    results_json TEXT,         -- serialized AnalysisState JSON after completion (avoids re-running graph)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    holding_id TEXT,
    ticker TEXT NOT NULL,
    severity TEXT NOT NULL,        -- none | low | medium | high | critical
    risk_category TEXT NOT NULL,   -- financial_health | liquidity | revenue_concentration | etc.
    summary TEXT NOT NULL,
    evidence_json TEXT NOT NULL,   -- JSON: list of {citation_anchor, text, source_url}
    risk_score REAL,
    score_delta REAL,
    confidence REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (job_id) REFERENCES analysis_jobs(id),
    FOREIGN KEY (holding_id) REFERENCES holdings(id)
);

CREATE TABLE IF NOT EXISTS disclosure_changes (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    section TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    year_a TEXT NOT NULL,
    year_b TEXT NOT NULL,
    change_type TEXT NOT NULL,  -- new_risk | removed_risk | intensified_language | softened_language | metric_changed | legal_accounting_update
    materiality TEXT NOT NULL,  -- high | medium | low
    confidence REAL NOT NULL,
    summary TEXT NOT NULL,
    old_text TEXT,
    new_text TEXT,
    old_citation_anchor TEXT,
    new_citation_anchor TEXT,
    old_source_url TEXT,
    new_source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (job_id) REFERENCES analysis_jobs(id)
);

-- Indexes for common query patterns

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON holdings(ticker);

CREATE INDEX IF NOT EXISTS idx_documents_ticker ON documents(ticker);
CREATE INDEX IF NOT EXISTS idx_documents_type_date ON documents(filing_type, filed_at);
CREATE INDEX IF NOT EXISTS idx_documents_accession ON documents(accession_number);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON chunks(ticker);
CREATE INDEX IF NOT EXISTS idx_chunks_ticker_type_date ON chunks(ticker, filing_type, filed_at);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(text_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_citation ON chunks(citation_anchor);

CREATE INDEX IF NOT EXISTS idx_jobs_portfolio ON analysis_jobs(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON analysis_jobs(status);

CREATE INDEX IF NOT EXISTS idx_findings_portfolio ON findings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_findings_job ON findings(job_id);
CREATE INDEX IF NOT EXISTS idx_findings_ticker ON findings(ticker);

CREATE INDEX IF NOT EXISTS idx_changes_job ON disclosure_changes(job_id);
CREATE INDEX IF NOT EXISTS idx_changes_ticker ON disclosure_changes(ticker);

-- FTS5 virtual table for BM25 keyword search
-- Populated automatically via trigger on chunks insert

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    ticker UNINDEXED,
    filing_type UNINDEXED,
    filed_at UNINDEXED,
    section UNINDEXED,
    citation_anchor UNINDEXED,
    content='chunks',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS chunks_fts_insert
AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text, ticker, filing_type, filed_at, section, citation_anchor)
    VALUES (new.rowid, new.text, new.ticker, new.filing_type, new.filed_at, new.section, new.citation_anchor);
END;

CREATE TRIGGER IF NOT EXISTS chunks_fts_delete
AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, ticker, filing_type, filed_at, section, citation_anchor)
    VALUES ('delete', old.rowid, old.text, old.ticker, old.filing_type, old.filed_at, old.section, old.citation_anchor);
END;
