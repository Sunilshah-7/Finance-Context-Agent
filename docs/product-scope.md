# Product and Scope

## One-Sentence Pitch

FinContext Agent tells investors what changed in financial documents and what those changes mean for their actual portfolio.

## Primary User

An analyst, portfolio manager, or advanced investor who tracks multiple holdings and wants to understand how new filings, earnings transcripts, and disclosures affect portfolio risk.

## Core Jobs

1. Upload or connect a portfolio.
2. Ingest filings and transcripts for the companies in the portfolio.
3. Detect material changes across filings over time.
4. Retrieve relevant citations from source documents.
5. Produce portfolio-aware impact memos.
6. Score risk by company, holding, sector, and portfolio exposure.
7. Explain why scores changed and which source passages support the conclusion.

## Hackathon MVP

The MVP should support:

- Portfolio CSV upload with ticker, shares, cost basis, optional sector, and target allocation.
- Filing ingestion for 10-K and 10-Q documents for 5-20 tickers.
- Earnings transcript ingestion through a prepared sample dataset or a licensed API.
- Search and question answering over filings.
- Disclosure diff between the latest filing and prior filing.
- Risk score from 0-100 per holding.
- Portfolio impact memo with inline citations.
- Dashboard with exposure heatmap, top risks, recent changes, and cited findings.

## Optional Track 3 Extension

Add multimodal PDF and table understanding:

- PDF page rendering and layout-aware extraction.
- Table extraction from financial statements.
- Chart/image summarization from investor presentations.
- Cross-checks between narrative disclosures and financial tables.

## Non-Goals for MVP

- Automated trading or broker order placement.
- Personalized financial advice.
- Real-time market making.
- Full replacement for legal/compliance review.
- Guaranteed materiality classification.

All UI copy should clearly frame outputs as research assistance, not investment advice.

