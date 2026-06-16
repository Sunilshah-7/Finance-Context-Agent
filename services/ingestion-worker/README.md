# Ingestion Worker

Live EDGAR ingestion is target work, not part of the current runnable stack.
`README.md` is the source of truth: the app currently ships fixture data while
the ingestion pipeline is still to build.

This directory is reserved for a future one-shot ingestion worker. Do not treat
the commands below as implemented until the corresponding files exist.

## Target Responsibilities

1. Resolve tickers to SEC CIKs.
2. Fetch EDGAR filing lists and HTML filing documents.
3. Parse HTML sections such as Item 1, Item 1A, Item 7, Item 7A, and Item 8.
4. Chunk sections with stable citation anchors.
5. Generate embeddings through the Inference Gateway.
6. Upsert vectors/payloads into Qdrant collection `fincontext_chunks`.
7. Write chunk text and metadata to SQLite for retrieval.
8. Validate row counts, citation anchors, and source URLs.

## Target Constraints

- EDGAR HTML only for MVP.
- No PDF parsing.
- No live ingestion during the judge demo.
- `SEC_USER_AGENT` must identify the app and include a contact email.
- Embeddings and reranking must go through the Inference Gateway, never directly
  to model backends.

## Current Status

Implemented elsewhere today:

- Agent API fixture mode.
- Gateway `/v1/embeddings` passthrough route.
- Gateway `/v1/rerank` passthrough route.
- Qdrant collection health/setup from the Agent API.

Still to build here:

- EDGAR client.
- HTML parser.
- Chunker.
- SQLite document/chunk writes.
- Qdrant vector upserts.
- Validation CLI.
- Snapshot/export helpers for ingested demo data.

See `docs/data-and-retrieval.md` and `docs/ingestion-output-contract.md` for
target data contracts.
