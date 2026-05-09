# Ingestion Output Contract

This is the quick handoff for retrieval, memo generation, and UI citation-card
work. The ingestion foundation is already merged into `dev` through PR #17.

## Is Chunking, Embedding, SQLite, and Qdrant Done?

Yes, the foundation exists.

- Chunking: `services/ingestion-worker/worker/chunking.py`
- Embeddings through Gateway: `services/ingestion-worker/worker/embeddings.py`
- SQLite document/chunk writes: `services/ingestion-worker/worker/db.py`
- Qdrant payload/vector upserts: `services/ingestion-worker/worker/vector_store.py`
- Shared row/payload schemas: `packages/schemas/python/db.py`
- Physical SQLite schema and FTS triggers: `infra/schema.sql`

What is not done yet: a real AMD VM ingestion run against live Gateway/Qdrant.
The code is unit-tested, but demo data still has to be loaded and validated on
the runtime environment.

## SQLite Output

Ingestion writes one row per filing to `documents` and one row per evidence
chunk to `chunks`.

Important `chunks` fields for retrieval/UI:

- `id`: chunk UUID and Qdrant point id.
- `document_id`: joins back to `documents.id`.
- `ticker`: portfolio/retrieval filter, for example `AMD`.
- `filing_type`: `10-K` or `10-Q`.
- `filed_at`: filing date as ISO text.
- `section`: normalized section id, for example `item_1a`.
- `item_label`: citation-facing label, for example `Item 1A`.
- `section_title`: human title, for example `Risk Factors`.
- `chunk_index`: stable ordering within the document.
- `text`: full chunk text for BM25 and display.
- `text_hash`: dedupe key.
- `token_count`: chunk size estimate.
- `citation_anchor`: exact source anchor, for example `AMD 10-K Item 1A paragraph 42`.
- `source_url`: SEC filing URL.
- `is_table`: `1` for table chunks, `0` for paragraph chunks.
- `vector_id`: same value as `id`, linking SQLite to Qdrant.

`chunks_fts` is populated by SQLite triggers in `infra/schema.sql`, so retrieval
can run BM25 over `chunks.text` without a separate indexing job.

## Qdrant Output

Ingestion upserts vectors into collection `fincontext_chunks`.

The Qdrant point id is the same value as SQLite `chunks.id`. The vector is the
1024-dimensional embedding returned by Gateway `/v1/embeddings`. The payload is
built from `QdrantChunkPayload` and includes:

- `chunk_id`
- `document_id`
- `ticker`
- `cik`
- `company_name`
- `filing_type`
- `accession_number`
- `filed_at`
- `fiscal_period`
- `section`
- `item_label`
- `section_title`
- `chunk_index`
- `token_count`
- `text`
- `text_hash`
- `citation_anchor`
- `source_url`
- `is_table`

Kishan can use either SQLite rows or Qdrant payloads to render citation cards.
The safest join key is:

```text
SQLite chunks.id == SQLite chunks.vector_id == Qdrant point id == Qdrant payload.chunk_id
```

## Citation Anchor Rules

Paragraph chunks:

```text
{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}
```

Table chunks:

```text
{TICKER} {FILING_TYPE} {SECTION_LABEL} table {N}
```

Examples:

```text
AMD 10-K Item 1A paragraph 42
AMD 10-K Item 8 table 3
```

These anchors are generated during chunking before embeddings or storage. The
validation follow-up branch checks sampled anchors against this format.

## Retrieval Starting Points

For BM25, query `chunks_fts` and join back to `chunks` by `rowid`.

For vector retrieval, search Qdrant collection `fincontext_chunks` with payload
filters such as:

- `ticker = "AMD"`
- `filing_type in ["10-K", "10-Q"]`
- `section in ["item_1a", "item_7"]`
- `filed_at` bounded by the retrieval plan date range

The validation helpers merged in PR #22 can confirm:

- SQLite `chunks` are searchable through `chunks_fts`;
- Qdrant point count matches SQLite chunk count;
- citation anchors match paragraph/table format;
- documents can be summarized by ticker and filing type.
