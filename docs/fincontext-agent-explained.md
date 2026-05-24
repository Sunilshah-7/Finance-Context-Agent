# FinContext Agent Explained From Zero

This document explains what we are building, what has already been built, why
each part exists, and how the parts connect. It is written for a teammate who
did not personally write the code and wants to understand the project clearly.

## 1. The One-Sentence Version

FinContext Agent reads SEC filings for a portfolio, finds meaningful changes in
risk language over time, and writes a citation-backed analyst memo explaining
which holdings may have higher risk.

## 2. The Product In Plain English

Imagine you own a small portfolio:

```text
AMD, NVDA, MSFT, JPM, TSLA
```

Each of those companies files long reports with the SEC. These reports include
risk factors, business descriptions, financial discussion, market risk tables,
and other disclosures.

A normal investor or analyst might not read every paragraph every year. The
useful question is:

```text
Did the company quietly change how it talks about risk?
```

For example, suppose one year's filing says:

```text
We depend on third-party manufacturers.
```

Then the next year's filing says:

```text
We depend on a limited number of third-party manufacturers, and disruptions may
materially and adversely affect our ability to meet customer demand.
```

That second sentence is stronger. It may signal that the risk became more
important or that management is disclosing it more seriously.

FinContext Agent is designed to find those changes, connect them to the user's
portfolio, and produce a memo with exact citations.

## 3. What This Is Not

This project is intentionally narrow.

It is not a stock-picking tool. It must not say buy, sell, hold, short, or make
investment recommendations.

It is not live market data. It does not need real-time prices for the MVP.

It is not a broker integration. It does not connect to trading accounts.

It is not a generic chatbot over random documents. It is a filing-analysis
workflow with citation discipline.

It is not supposed to ingest live SEC data during the judge demo. We pre-ingest
data before demo time so the demo feels fast and stable.

## 4. Why The Inference Gateway Matters

The current MVP uses NVIDIA NIM hosted inference behind a provider-agnostic Gateway. The architectural story is:

```text
Agent API and ingestion code call one Gateway contract, not a vendor-specific SDK.
```

The important model split remains the same: a smaller planner model handles
retrieval planning and disclosure classification, while a larger reasoner model
writes the final analyst memo.

We can tell judges:

```text
The workflow is insulated from the serving backend. Today the Gateway routes chat completions to NVIDIA NIM.
```

We still use the smaller planner model for cheaper intermediate tasks, because
using the large model for everything would waste latency and hosted inference
budget.

## 5. The Main Services

There are four major software areas.

### 5.1 Ingestion Worker

Path:

```text
services/ingestion-worker/
```

Purpose:

```text
Download SEC filings, parse them, chunk them, embed them, and store them.
```

This is not a web server. It is a command-line tool that runs before demo day.

The ingestion worker is already implemented as a foundation.

### 5.2 Inference Gateway

Path:

```text
services/inference-gateway/
```

Purpose:

```text
Be the single doorway to every model service.
```

Instead of letting every part of the app call NIM or embedding backends directly, everything
goes through the Gateway. This gives us one place for request IDs, logging,
metrics, routing, and error normalization.

Gateway routes:

```text
/v1/chat/completions with fincontext-planner  -> 14B planner model
/v1/chat/completions with fincontext-reasoner -> 72B reasoner model
/v1/embeddings                                -> embedding model
/v1/rerank                                    -> reranker model
```

### 5.3 Agent API

Path:

```text
services/agent-api/
```

Purpose:

```text
Receive UI/API requests and run the LangGraph workflow.
```

This is where portfolio upload, job creation, retrieval, disclosure change
classification, risk scoring, and final memo generation will connect.

As of this writing, PR #19 for Agent API exists but is marked "DONOT MERGE THIS
PR: Still in review". Do not build on it until Sunil says it is ready.

### 5.4 Demo UI

Path:

```text
apps/demo-ui/
```

Purpose:

```text
React app deployed on HuggingFace Spaces for judges.
```

The UI should call the Agent API. It should not call model services directly.

## 6. The Data Stores

There are two important data stores.

### 6.1 SQLite

SQLite is a normal file database. Our database file will be called something
like:

```text
fincontext.db
```

SQLite stores structured metadata:

- portfolios
- holdings
- filings/documents
- chunks
- analysis jobs
- findings

The `chunks` table stores the actual chunk text. This matters because keyword
retrieval uses SQLite FTS5, which is a built-in full-text search feature.

### 6.2 Qdrant

Qdrant is the vector database. It stores embeddings.

An embedding is a list of numbers that represents the meaning of text. For this
project, each chunk gets a 1024-dimensional vector from BGE-large.

Qdrant lets us ask:

```text
Which filing chunks are semantically close to this question?
```

SQLite answers keyword questions. Qdrant answers semantic similarity questions.
We use both because financial retrieval needs both.

## 7. What A Chunk Is

SEC filings are long. A 10-K can be hundreds of pages. We cannot treat the whole
filing as one retrieval unit.

So we split each relevant section into chunks.

A chunk is a smaller piece of text, usually around 600 to 1000 tokens, with
metadata attached.

Example chunk metadata:

```text
ticker: AMD
filing_type: 10-K
section: item_1a
item_label: Item 1A
chunk_index: 42
citation_anchor: AMD 10-K Item 1A paragraph 42
source_url: SEC filing URL
```

The chunk text is stored in SQLite. The chunk embedding is stored in Qdrant.

The same id connects both:

```text
SQLite chunks.id == SQLite chunks.vector_id == Qdrant point id == Qdrant payload.chunk_id
```

That is the most important join rule for Kishan's retrieval/UI work.

## 8. What Embeddings Are

An embedding is a numeric representation of text.

If two pieces of text mean similar things, their embeddings should be close in
vector space.

Example:

```text
"supply chain risk"
"third-party manufacturing dependency"
```

These phrases do not share all the same words, but they are related. Keyword
search might miss some matches. Vector search can find them because the
embedding model understands meaning.

In our project:

- chunk text goes to Gateway `/v1/embeddings`;
- Gateway routes that to the embedding backend;
- the embedding service returns a 1024-number vector;
- ingestion writes that vector to Qdrant.

## 9. What Reranking Means

Kishan asked about "rank them". This is the retrieval/reranking part.

A retrieval system usually finds a first set of candidate chunks. Some are very
good. Some are only loosely related.

Reranking means:

```text
Take candidate chunks and sort them by how well they answer the exact question.
```

The intended retrieval flow is:

1. User asks a question.
2. Embed the question through Gateway `/v1/embeddings`.
3. Search Qdrant for semantically similar chunks.
4. Search SQLite FTS5 for keyword/BM25 matches.
5. Merge those two candidate lists using Reciprocal Rank Fusion.
6. Send candidate text to Gateway `/v1/rerank`.
7. Keep the best-ranked chunks.
8. Return those chunks with citation anchors.

The ingestion work gives Kishan the chunks and vectors. His retrieval work uses
them.

## 10. What BM25 Means

BM25 is a keyword search ranking method. It is good at exact words and phrases.

Example query:

```text
export controls China advanced AI accelerators
```

BM25 is good at finding chunks that literally include words like "export",
"China", and "controls".

Vector search is good at meaning. BM25 is good at exact language. We use both.

## 11. What Reciprocal Rank Fusion Means

Reciprocal Rank Fusion, or RRF, is a simple way to merge two ranked lists.

Suppose BM25 says:

```text
1. chunk A
2. chunk B
3. chunk C
```

And Qdrant says:

```text
1. chunk B
2. chunk D
3. chunk A
```

RRF gives points based on rank and combines them. A chunk that ranks well in both
lists rises to the top.

This avoids choosing only keyword search or only vector search.

## 12. What Disclosure Drift Means

Disclosure drift means the company changed how it describes a topic across
filings.

The change types we care about include:

- `new_risk`: a risk appears that was not there before.
- `removed_risk`: a risk disappears.
- `intensified_language`: the same risk is described more strongly.
- `softened_language`: the same risk is described less strongly.
- `metric_changed`: a number changed.
- `legal_accounting_update`: a regulatory/accounting update changed the text.

Example of intensified language:

```text
Old: We depend on suppliers.
New: We depend on a limited number of suppliers, and disruptions could materially harm operations.
```

The second version is stronger and more specific.

## 13. What LangGraph Does

LangGraph is the workflow engine for the Agent API.

Our graph has four nodes:

```text
portfolio_context_planner
filing_retrieval
disclosure_change
analyst_memo
```

### Node 1: portfolio_context_planner

This node looks at the user's portfolio and question. It decides which tickers,
filing types, sections, dates, and keywords should be searched.

It uses the 14B model.

### Node 2: filing_retrieval

This node retrieves evidence chunks from SQLite and Qdrant.

It does not generate claims. It only returns evidence.

It uses no LLM, but it does call the Gateway reranker.

### Node 3: disclosure_change

This node compares retrieved chunks across filing dates and classifies changes.

It uses the 14B model.

### Node 4: analyst_memo

This node computes risk scores and writes the final memo.

It uses the 72B model.

It must verify citations and include the required investment-research
disclaimer.

## 14. What Has Already Been Built

### PR #17: Ingestion Worker Foundation

Built:

- EDGAR client.
- SEC HTML parser.
- paragraph-aware chunker.
- embedding client through Gateway.
- SQLite document/chunk writer.
- Qdrant payload/vector writer.
- ingestion CLI.
- focused ingestion tests.

Why it matters:

```text
This creates the data that retrieval, reranking, memo generation, and citation cards need.
```

### PR #18: Demo Data Snapshot Ops

Built:

- SQLite backup helper.
- Qdrant snapshot helper.
- JSON manifest linking backup and snapshot.
- runbook for demo data preservation.

Why it matters:

```text
After we load demo data once, we can preserve and restore the exact demo corpus.
```

### PR #20: Inference Gateway Foundation

Built:

- Gateway routing for chat, embeddings, reranking, health, and metrics.

Why it matters:

```text
Every model call goes through one controlled Gateway instead of many direct service calls.
```

### PR #21: Explanation And Output Contract Docs

Built:

- handoff docs explaining agent-built work.
- ingestion output contract for Kishan.
- module-level explanations in Codex-owned files.

Why it matters:

```text
The team can understand and review the work without reverse-engineering commit history.
```

### PR #22: Ingestion Validation Helpers

Built:

- SQLite FTS validation helper.
- Qdrant point-count validation helper.
- citation-anchor inspection helper.
- document summary helper.

Why it matters:

```text
After real ingestion, we can verify the data is actually usable.
```

### PR #23: Retrieval Fixture Scaffolding

Status:

```text
Open for review.
```

Adds planned retrieval queries and planned disclosure-change targets. These are
not final ground-truth labels yet because we do not have real ingested chunk IDs.

### PR #24: Ingestion Validation CLI

Status:

```text
Open for review.
```

Wraps the validation helpers in one command so the one-filing smoke check is
easy to run.

## 15. What Is Not Done Yet

The biggest unfinished items are:

- Backend runtime is not fully provisioned/validated yet.
- NVIDIA NIM credentials and live Gateway routing are not confirmed yet.
- Real AMD one-filing ingestion has not been run.
- Full demo corpus has not been loaded.
- Agent API is not merged and ready.
- Retrieval pipeline is not implemented in Agent API.
- LangGraph nodes are not implemented.
- React UI is not wired end to end.
- Demo video and final submission are not done.

## 16. The Critical Path From Here

The next practical order is:

1. Merge documentation and validation PRs after review.
2. Get the backend, Gateway, NIM routing, and Qdrant running.
3. Run one AMD 10-K ingestion smoke.
4. Validate SQLite, Qdrant, citation anchors, and document summaries.
5. Run full demo corpus ingestion.
6. Fill eval fixtures with real chunk IDs and citation anchors.
7. Implement retrieval pipeline.
8. Implement LangGraph nodes.
9. Wire Agent API to React UI.
10. Rehearse and record demo.

## 17. What To Say If Asked "What Did You Do?"

Say this:

```text
I used agents to implement and document the ingestion/data foundation. The work
does not change the architecture. It follows AGENTS.md: pre-ingest SEC filings,
chunk them with citation anchors, embed chunks through the Gateway, store text
in SQLite, store vectors in Qdrant, and add validation/backup tools so the team
can verify and preserve demo data.
```

Then add:

```text
Kishan's reranking work depends on this. We now have chunks and vectors. His
retrieval flow should search SQLite BM25 and Qdrant, merge candidates, call the
Gateway reranker, and return citation-ready chunks to the graph and UI.
```

## 18. What To Say If Asked "Is Embedding Done?"

Say this:

```text
The ingestion-side embedding client is done. It sends chunk text to the
Inference Gateway `/v1/embeddings` endpoint and validates 1024-dimensional
vectors before writing them to Qdrant. What is not done yet is a real backend run
against live Gateway and Qdrant services.
```

## 19. What To Say If Asked "Is Ranking Done?"

Say this:

```text
No. Candidate data exists, and the Gateway has a rerank endpoint foundation, but
the retrieval pipeline that combines BM25, Qdrant vector search, RRF, and
reranking still needs to be implemented. That is Kishan's retrieval work, with
Abhiyan reviewing the ingestion data contract.
```

## 20. What To Say If Asked "Can We Demo This Now?"

Say this:

```text
<<<<<<< HEAD
Not yet. We have important foundations merged, but the AMD VM, real ingestion
=======
Not yet. We have important foundations merged, but the backend, real ingestion
>>>>>>> origin/dev
run, retrieval pipeline, Agent API graph, and React UI still need integration.
We should not live-ingest during the judge demo. We should pre-ingest, validate,
snapshot, and then demo from stable data.
```

## 21. Mental Model

Think of the whole system like a library.

Ingestion is the librarian who reads every filing, cuts it into labeled cards,
and stores each card in two places:

- SQLite, for keyword lookup and exact text;
- Qdrant, for meaning-based lookup.

Retrieval is the person who finds the best cards for a question.

Reranking is the person who sorts those cards from most useful to least useful.

The LangGraph workflow is the analyst who uses the cards to compare old and new
filings, score risk, and write a memo.

The UI is the front desk where the user uploads a portfolio and reads the memo.

The Gateway is the security desk: every model request goes through it.

NVIDIA NIM is the hosted inference layer that makes the large reasoner model
available to the final memo step.

## 22. Simple Glossary

SEC:
The U.S. Securities and Exchange Commission.

EDGAR:
The SEC's public filing database.

10-K:
Annual company filing.

10-Q:
Quarterly company filing.

Item 1A:
Risk Factors section in many filings.

Chunk:
A smaller piece of filing text with metadata and a citation anchor.

Citation anchor:
A stable label that points back to a filing chunk, such as
`AMD 10-K Item 1A paragraph 42`.

Embedding:
A numeric representation of text meaning.

Vector store:
A database for searching embeddings. We use Qdrant.

BM25:
A keyword ranking algorithm. SQLite FTS5 gives us this style of search.

Reranker:
A model that re-sorts candidate chunks by relevance to a specific question.

LangGraph:
The workflow system that runs the 4-node agent pipeline.

Inference Gateway:
The single API layer that routes model, embedding, and rerank calls.

Snapshot:
A saved copy of Qdrant vector data.

SQLite backup:
A saved copy of the metadata database.
