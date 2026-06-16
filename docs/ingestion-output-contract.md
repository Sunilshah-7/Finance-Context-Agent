# Ingestion Output Contract

`README.md` is the source of truth. Live ingestion is not implemented in the
current runnable stack. This document describes the target output contract for
the future ingestion worker.

## Target SQLite Output

Future ingestion should write one row per filing to `documents` and one row per
evidence chunk to `chunks`.

Important target `chunks` fields:

- `id`: chunk UUID and Qdrant point id.
- `document_id`: joins back to `documents.id`.
- `ticker`: retrieval filter, for example `AMD`.
- `filing_type`: `10-K` or `10-Q`.
- `filed_at`: filing date as ISO text.
- `section`: normalized section id.
- `item_label`: citation-facing label, for example `Item 1A`.
- `section_title`: human title, for example `Risk Factors`.
- `chunk_index`: stable ordering within the document.
- `text`: full chunk text for retrieval and display.
- `text_hash`: dedupe key.
- `token_count`: chunk size estimate.
- `citation_anchor`: exact source anchor, for example `AMD 10-K Item 1A paragraph 42`.
- `source_url`: SEC filing URL.
- `is_table`: table marker.
- `vector_id`: same value as `id`, linking SQLite to Qdrant.

The current Go SQLite store does not yet include these tables.

## Target Qdrant Output

Future ingestion should upsert vectors into collection `fincontext_chunks`.

The Qdrant point id should match SQLite `chunks.id`. Payload fields should
include:

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

Join invariant:

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

## Validation Goals

When ingestion is implemented, validation should confirm:

- SQLite chunk count is nonzero.
- Qdrant point count matches SQLite chunk count.
- citation anchors match the paragraph/table format.
- source URLs are populated.
- repeated ingestion is idempotent.
