# Data and Retrieval

## Data Sources

MVP sources:

- SEC 10-K, 10-Q, and 8-K filings.
- Company annual reports and investor PDFs.
- Prepared earnings transcript samples.
- User portfolio CSV.

Production sources:

- Licensed transcript feeds.
- Market data provider for prices and holdings valuation.
- Broker/custodian integrations.
- News and regulatory alerts.
- XBRL company facts.

## Document Normalization

Normalize all sources into this shape:

```json
{
  "document_id": "doc_123",
  "ticker": "AMD",
  "cik": "0000002488",
  "document_type": "10-K",
  "filed_at": "2026-02-15",
  "source_url": "https://...",
  "sections": [
    {
      "section_id": "item_1a",
      "title": "Item 1A. Risk Factors",
      "text": "...",
      "tables": [],
      "anchors": []
    }
  ]
}
```

## Chunking Rules

- Preserve section hierarchy.
- Keep chunks around 600-1,000 tokens.
- Overlap 80-150 tokens.
- Do not split table rows across chunks.
- Add citation anchors at paragraph and table level.
- Store token counts and checksums.

## Embeddings

Recommended models:

- `BAAI/bge-large-en-v1.5` for general English retrieval.
- `intfloat/e5-large-v2` for strong query/document retrieval.
- Finance-tuned embedding models only after testing citation precision.

Run embeddings on AMD GPU for batch indexing. For small demo workloads, CPU embedding is acceptable but should not be the benchmark path.

## Reranking

Recommended model:

- `BAAI/bge-reranker-large`.

Run reranking on AMD GPU because reranking dominates latency when comparing many chunks across multiple filings.

## Metadata Filters

Each chunk should include:

- ticker.
- CIK.
- company name.
- filing type.
- filing date.
- fiscal period.
- section title.
- item label.
- accession number.
- source URL.
- R2 object key.
- citation anchor.
- portfolio ID only for private user uploads.

## Citation Format

Use compact source tags in the UI:

```text
[AMD 10-K, Item 1A, filed 2026-02-15, paragraph 42]
```

Store full source metadata separately:

```json
{
  "source_url": "https://www.sec.gov/Archives/...",
  "r2_key": "filings/AMD/2026/10-k/source.html",
  "page": null,
  "section": "Item 1A. Risk Factors",
  "paragraph": 42,
  "char_start": 18422,
  "char_end": 19080
}
```

