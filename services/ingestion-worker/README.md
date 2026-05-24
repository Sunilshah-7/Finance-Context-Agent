# services/ingestion-worker

Python CLI worker for SEC EDGAR filing ingestion. Fetches HTML filings, parses them into sections, chunks them with citation anchors, generates BGE embeddings, and upserts into Qdrant and SQLite.

This is a one-shot script, not a long-running server. It is run before the demo to pre-populate the vector store and metadata database.

## What this service does

1. Resolves tickers to SEC CIKs using `https://www.sec.gov/files/company_tickers.json`
2. Fetches filing lists from `https://data.sec.gov/submissions/CIK{cik}.json`
3. Downloads HTML filing documents from EDGAR Archives
4. Parses HTML into sections by item label (Item 1, Item 1A, Item 7, Item 7A, Item 8)
5. Splits sections into overlapping chunks (600–1,000 tokens, 100-token overlap)
6. Assigns citation anchors: `{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}`
7. Generates 1024-dimensional BGE embeddings via the Inference Gateway
8. Upserts chunks to Qdrant (`fincontext_chunks` collection) with full payload metadata
9. Upserts chunk metadata to SQLite (`chunks` table, FTS5 index auto-populated via trigger)

**MVP scope: EDGAR HTML only. No PDF parsing.**

## Stack

- Python 3.12
- httpx (async HTTP client for EDGAR + Inference Gateway)
- BeautifulSoup4 + lxml (HTML parsing)
- tiktoken (token counting for chunk sizing)
- qdrant-client (vector store upsert)
- sqlite3 (metadata and FTS5 index)

## File Structure

```
services/ingestion-worker/
  ingest.py            # CLI entry point — parse args, orchestrate pipeline
  worker/
    sec_client.py      # EDGAR REST API client, rate limiting, ticker→CIK resolution
    parsers/
      sec_html.py      # HTML section extractor by item label
    chunking.py        # Paragraph-aware chunker with citation anchor assignment
    embeddings.py      # Batch embedding via Inference Gateway /v1/embeddings
    vector_store.py    # Qdrant upsert with deduplication by text_hash
    db.py              # SQLite writes: documents, chunks tables
    models.py          # Pydantic models for the pipeline (FilingRef, NormalizedSection, ChunkInput, etc.)
  tests/
    test_sec_client.py  # Verify CIK resolution and filing URLs with mocked EDGAR HTTP
    test_parser.py      # Verify section extraction from small SEC-like HTML snippets
    test_chunking.py    # Verify chunk sizes, overlap, citation anchors
  requirements.txt
```

## Running

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Full pre-ingestion for demo corpus
python ingest.py \
  --tickers AMD,NVDA,MSFT,JPM,TSLA \
  --filing-types 10-K,10-Q \
  --years 4 \
  --db-path ../../fincontext.db \
  --qdrant-url http://localhost:6333 \
  --gateway-url http://localhost:8080

# Single ticker test
python ingest.py --tickers AMD --filing-types 10-K --years 1

# Export citation-ready samples for retrieval/UI handoff
python export_handoff.py \
  --db-path ../../fincontext.db \
  --tickers AMD \
  --sections "Item 1A,Item 7" \
  --limit 25 \
  --output ../../handoff-kishan-amd.json

# Tests (mocked/offline; no real EDGAR, Gateway, or Qdrant required)
pytest tests/test_parser.py -x
pytest tests/test_chunking.py -x
```

## Handoff Export For Retrieval And UI

After ingestion writes SQLite rows, `export_handoff.py` can produce a compact
JSON file for retrieval, reranking, memo, and citation-card work. It does not
call EDGAR, Gateway, Qdrant, or any model service.

The export includes:

- document metadata: ticker, CIK, filing type, filed date, fiscal period,
  accession number, source URL, parsed sections, and chunk count;
- chunk metadata: `chunk_id`, matching `qdrant_point_id`, `citation_anchor`,
  source URL, section, item label, token count, text hash, and table flag;
- `text_preview` for quick UI/retrieval inspection;
- optional full chunk text with `--include-full-text`.

Use it when Kishan needs sample citation-ready chunks before wiring retrieval,
reranking, or UI citation cards.

## EDGAR Rate Limiting

EDGAR limits requests to 10/second. The SEC client enforces this with an async rate limiter. A polite 0.1-second delay is also added between filing document downloads.

The `SEC_USER_AGENT` environment variable must be set. EDGAR blocks requests without a valid User-Agent that identifies the application and a contact email.

## Expected Output

After ingesting 5 tickers × 6 filings average:
```
[AMD] Resolved to CIK 0000002488
[AMD] Found 8 filings (4 10-K, 4 10-Q) in date range
[AMD] Processing AMD 10-K filed 2025-02-14 (accession: 0000002488-25-000012)
[AMD]   Parsed 6 sections: Item 1 (2847 words), Item 1A (8432 words), Item 7 (6120 words)...
[AMD]   Created 847 chunks, 3 batches for embedding
[AMD]   Embedded 847 chunks (avg 0.08s/batch)
[AMD]   Upserted 847 points to Qdrant, 847 rows to SQLite
...
Done. 5 tickers, 31 filings, 14,392 chunks. Total time: 1847s.
```

## Qdrant Payload Schema (per chunk)

Required fields (see `docs/data-and-retrieval.md` for full specification):
- `chunk_id`, `document_id`, `ticker`, `cik`, `filing_type`, `filed_at`, `fiscal_period`
- `section`, `item_label`, `section_title`
- `chunk_index`, `token_count`, `text`, `text_hash`
- `citation_anchor` — format: `AMD 10-K Item 1A paragraph 42`
- `source_url` — full EDGAR document URL
- `is_table` — bool, true for table chunks

## Demo Data Backups

After successful demo ingestion on the backend host, use `docs/demo-data-ops.md` to
create a SQLite backup, Qdrant snapshot, and manifest. Generated DBs, Qdrant
storage, snapshots, and `backups/` output are local artifacts and must not be
committed.
