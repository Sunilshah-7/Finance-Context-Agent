# Codex Work Handoff

This note explains the Codex-built work in human terms so teammates can review
the implementation without reading every commit.

## Current Git State

- PR #17, `feat/ingestion-worker-foundation`, is merged into `dev`.
- PR #18, `infra/demo-data-snapshots`, is merged into `dev`.
- PR #20, Kishan's Gateway foundation, is merged into `dev`.
- PR #19, `feat/agent-api`, is still open and explicitly marked "DONOT MERGE THIS PR: Still in review".
- `feat/ingestion-validation-tools` and `feat/ingestion-validation-cli` are pushed follow-up branches but are not merged into `dev` yet.

## What PR #17 Added

PR #17 added the ingestion worker foundation under `services/ingestion-worker/`.
This is a pre-demo CLI pipeline, not a live demo feature and not a server.

The pipeline works in this order:

1. Resolve ticker symbols to SEC CIKs using EDGAR company ticker metadata.
2. Fetch each company's SEC filing list from EDGAR submissions JSON.
3. Pick recent `10-K` and `10-Q` filings for the requested date range.
4. Download filing HTML from EDGAR Archives.
5. Parse SEC HTML into target sections: `Item 1`, `Item 1A`, `Item 7`, `Item 7A`, and `Item 8`.
6. Chunk section text into paragraph-aware evidence chunks and isolate tables.
7. Create stable citation anchors such as `AMD 10-K Item 1A paragraph 42`.
8. Send chunk text to the Inference Gateway `/v1/embeddings` endpoint.
9. Store chunk text and metadata in SQLite for BM25/FTS retrieval.
10. Store vectors and retrieval payloads in Qdrant collection `fincontext_chunks`.

The key architectural point: ingestion code never calls TEI or vLLM directly.
Embedding calls go through the Inference Gateway URL so the same routing layer
is used everywhere.

## Why Each Ingestion Piece Exists

- `ingest.py` is the CLI coordinator. It wires together EDGAR, parser, chunker,
  embeddings, SQLite, and Qdrant.
- `worker/sec_client.py` handles EDGAR-specific requirements: User-Agent,
  ticker-to-CIK lookup, request rate limiting, and local HTML cache.
- `worker/parsers/sec_html.py` turns messy EDGAR HTML into normalized filing
  sections we can safely chunk.
- `worker/chunking.py` creates retrieval-sized evidence chunks and assigns
  citation anchors before storage.
- `worker/embeddings.py` batches Gateway embedding requests and validates
  1024-dimensional BGE vectors.
- `worker/db.py` writes documents/chunks to SQLite. The FTS5 table is populated
  by triggers from `infra/schema.sql`.
- `worker/vector_store.py` builds shared-schema Qdrant payloads and upserts
  vectors into `fincontext_chunks`.
- The ingestion tests use mocked HTTP, temporary SQLite, and small HTML fixtures
  so they run without EDGAR, Gateway, or Qdrant.

## What PR #18 Added

PR #18 added demo data backup and snapshot ops.

The main script is `infra/ops/demo_data_snapshots.py`. After a successful demo
ingestion run, it can:

- copy `fincontext.db` to a timestamped backup using SQLite's backup API;
- request a Qdrant snapshot for the `fincontext_chunks` collection;
- write a JSON manifest tying the SQLite backup path to the Qdrant snapshot
  name.

The runbook is `docs/demo-data-ops.md`. Generated backup files live under
`backups/`, which is gitignored. SQLite DBs, Qdrant storage, model caches, and
snapshots should not be committed.

## Pending Follow-Up Branches

`feat/ingestion-validation-tools` adds helpers to verify ingestion output after
real services exist:

- SQLite `chunks` rows are searchable through `chunks_fts`;
- Qdrant point count matches SQLite chunk count;
- sampled citation anchors match paragraph/table anchor format;
- ingested documents can be summarized by ticker, filing type, filed date,
  parsed sections, and chunk count.

`feat/ingestion-validation-cli` adds one CLI wrapper around those helpers so the
AMD one-filing smoke check is a command instead of a Python snippet.

Merge order should be:

1. `feat/ingestion-validation-tools` into `dev`;
2. then rebase and merge `feat/ingestion-validation-cli` into `dev`.

Do not merge the CLI branch first because it depends on helper code from the
validation-tools branch.

## What Is Safe Versus Not Safe

Safe to review/merge after tests pass:

- documentation/comment-only cleanup;
- ingestion validation helpers after rebasing onto current `dev`;
- validation CLI after validation helpers merge;
- infra backup/snapshot tooling already merged in PR #18.

Not safe without coordination:

- shared schema changes under `packages/schemas/`;
- live demo ingestion inside UI flows;
- direct calls from Agent API nodes to TEI or vLLM;
- buy/sell/hold recommendation behavior;
- self-merging PRs without teammate review.

## How To Explain This Work Quickly

The agent followed `AGENTS.md` and the agreed task plan. The work did not invent
a new architecture. It filled in the Codex-owned ingestion and infra pieces
needed before retrieval and graph work can be reliable.

PR #17 gives the project a way to pre-ingest SEC filings into SQLite and Qdrant
with citation-ready chunks. PR #18 gives the team a way to preserve that loaded
demo corpus once it exists. The validation branches are the next layer: they
check that SQLite, Qdrant, citation anchors, and document summaries line up
before the team depends on the data for retrieval, memo generation, and UI
citation cards.
