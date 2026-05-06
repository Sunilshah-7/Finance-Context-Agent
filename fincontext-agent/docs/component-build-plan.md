# Component Build Plan

## 1. Portfolio Model

Build shared schemas first.

Tables:

- `users`: id, email, created_at.
- `portfolios`: id, user_id, name, base_currency, created_at.
- `holdings`: id, portfolio_id, ticker, company_name, cik, shares, market_value, cost_basis, sector, weight.
- `documents`: id, ticker, cik, filing_type, accession_number, filed_at, source_url, r2_key, parsed_r2_key, checksum.
- `chunks`: id, document_id, section, item_label, chunk_index, text_hash, citation_anchor, token_count, vector_id.
- `analysis_jobs`: id, portfolio_id, status, job_type, created_at, started_at, completed_at, error.
- `findings`: id, portfolio_id, holding_id, severity, risk_category, summary, evidence_json, score_delta, created_at.

Implementation steps:

1. Define Pydantic schemas in `packages/schemas/python`.
2. Generate matching TypeScript types in `packages/schemas/typescript`.
3. Add D1 migration SQL.
4. Build CSV parser with validation for ticker, shares, value, sector, and custom tags.
5. Add ticker-to-CIK resolver with SEC company facts cache.

## 2. Document Ingestion

Input sources:

- SEC EDGAR company submissions and filing documents.
- Uploaded PDFs.
- Sample earnings transcripts for demo.
- Optional licensed transcript provider for production.

Pipeline:

1. Resolve ticker to CIK.
2. Find target filings by type and date window.
3. Download source document.
4. Store raw document in R2.
5. Parse into normalized markdown and structured sections.
6. Extract tables into CSV/JSON.
7. Create stable anchors: filing accession, section, page, paragraph, table cell range.
8. Chunk with overlap and section boundaries.
9. Generate embeddings on AMD GPU.
10. Upsert vector records with metadata.

Recommended libraries:

- SEC: `sec-api` if licensed, or direct EDGAR endpoints with SEC-compliant user agent.
- HTML: `beautifulsoup4`, `lxml`.
- PDF: `pymupdf`, `unstructured`, `docling`, or `marker`.
- Tables: `camelot`, `tabula`, `pymupdf`, `pandas`.
- Chunking: LlamaIndex node parsers or custom section-aware splitter.

## 3. Retrieval

Build retrieval as a deterministic service before adding agent behavior.

Retrieval API:

```http
POST /retrieve
{
  "portfolio_id": "p_123",
  "query": "What changed in liquidity risk disclosures?",
  "tickers": ["AMD", "NVDA"],
  "filing_types": ["10-K", "10-Q"],
  "date_range": {"from": "2024-01-01", "to": "2026-05-06"},
  "top_k": 20
}
```

Response includes chunk text, citation anchors, document metadata, scores, and reranker explanation.

Implementation steps:

1. Retrieve candidates from Vectorize or pgvector.
2. Retrieve keyword matches from SQLite FTS/Postgres full text/OpenSearch.
3. Merge results with reciprocal rank fusion.
4. Rerank using BGE reranker on AMD GPU.
5. Apply diversity by ticker, section, and filing date.
6. Return only citation-ready chunks.

## 4. Disclosure Diff

Disclosure diff is a key demo feature.

Inputs:

- Current filing section.
- Prior filing section.
- Portfolio context.

Steps:

1. Align comparable sections by filing type and item label.
2. Normalize boilerplate, whitespace, page headers, and XBRL artifacts.
3. Compute textual diff with semantic clustering.
4. Classify each change:
   - new risk.
   - removed risk.
   - intensified language.
   - softened language.
   - metric changed.
   - legal/accounting update.
   - boilerplate.
5. Ask LLM to summarize only material changes with citations.
6. Verify each cited claim maps to both old and new source anchors.

Useful heuristic:

- Treat language such as "may", "could", "materially", "adversely", "substantial", "uncertain", "depends", "concentration", "liquidity", "impairment", and "going concern" as risk-bearing terms, but require citation evidence before raising severity.

## 5. Risk Scoring

Score per holding and aggregate to portfolio.

Risk categories:

- Financial health.
- Liquidity and debt.
- Revenue concentration.
- Margin pressure.
- Regulatory/legal.
- Supply chain.
- Customer demand.
- Guidance credibility.
- Disclosure volatility.
- Macro/sector sensitivity.

Risk score formula:

```text
holding_risk = base_document_risk
             + disclosure_change_delta
             + exposure_weight_modifier
             + concentration_modifier
             + recency_modifier
             + confidence_modifier
```

Output:

- 0-100 score.
- score delta vs prior run.
- evidence list.
- confidence level.
- recommended analyst follow-up questions.

Do not output buy/sell/hold commands. Phrase as research impact and risk monitoring.

## 6. Analyst Memo

Memo structure:

1. Executive summary.
2. Portfolio exposure affected.
3. Top changes since prior filing.
4. Risk score changes.
5. Evidence table with citations.
6. Watchlist questions for next earnings call.
7. Limitations and confidence.

Each paragraph that makes a factual claim should carry a citation reference.

## 7. Evaluation

Build evals before final demo polish.

Metrics:

- Citation precision: cited chunk actually supports the claim.
- Retrieval recall: known relevant sections are retrieved.
- Diff quality: material changes are detected and boilerplate ignored.
- Score stability: repeated runs produce consistent scores.
- Latency: time per filing and per portfolio.
- Throughput: concurrent analysis jobs on AMD GPU.
- Cost proxy: GPU seconds per analyzed document.

