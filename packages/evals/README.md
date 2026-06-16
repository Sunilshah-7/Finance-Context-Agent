# packages/evals

Evaluation harness for future retrieval quality, citation precision, disclosure
diff accuracy, and inference performance benchmarks.

Run evals after the full live pipeline is working and before demo polish. The
current runnable app uses fixture metrics from `data/fixtures/metrics.json`.

## Eval Suites

### 1. Retrieval Recall (`eval_retrieval.py`)

Tests whether the hybrid retrieval pipeline returns known-relevant chunks for labeled queries.

```bash
python eval_retrieval.py --db-path ../../fincontext.db --qdrant-url http://localhost:6333

# Expected output:
# Query: "AMD supply chain third-party manufacturing"
# Recall@20: 0.85 (17/20 known relevant chunks retrieved)
# Mean reciprocal rank: 0.74
```

Fixtures: `fixtures/labeled_queries.json` — 20 planned retrieval queries for
the demo corpus. Before real ingestion, `expected_chunk_ids` is intentionally
empty and `label_status` is `planned_pending_ingestion`. After AMD/NVDA/MSFT/JPM/TSLA
are ingested, fill in chunk IDs or citation anchors by manually reviewing the
retrieved evidence.

### 2. Citation Precision (`eval_citations.py`)

Tests whether citations in generated memos actually support the claims they cite.

```bash
python eval_citations.py --memo-path ../../demo/sample_memo.json

# Expected output:
# Citation pass rate: 0.94 (47/50 citations verified)
# Removed sentences: 3
```

Manual eval: for the 5-stock demo portfolio, read the generated memo and verify 10 random citations link to actually relevant text.

### 3. Disclosure Diff Quality (`eval_diff.py`)

Tests whether the disclosure_change node correctly classifies known real changes.

```bash
python eval_diff.py --db-path ../../fincontext.db

# Expected output:
# AMD supply chain: intensified_language — CORRECT
# AMD export controls (new 2025): new_risk — CORRECT
# TSLA customer concentration: intensified_language — CORRECT
# Accuracy: 9/10
```

Fixtures: `fixtures/known_changes.json` — 10 planned disclosure-change targets
with expected classifications. Before real ingestion, citation anchors are
`null` and `label_status` is `planned_pending_ingestion`. After the demo corpus
is loaded, replace the null anchors with manually verified old/new citations.

### 4. Latency Benchmark (`eval_latency.py`)

Runs 5 benchmark scenarios and records Gateway/NIM performance metrics.

```bash
python eval_latency.py --agent-api-url http://localhost:8090 --runs 3

# Runs each scenario 3 times and averages
# Expected output:
# Scenario: Single 10-K analysis (AMD 2025)
#   Avg latency: 32.4s | Tokens in: 8420 | Tokens out: 1850 | Tokens/sec: 52.3
#
# Scenario: 5-stock portfolio review
#   Avg latency: 91.2s | Tokens in: 22400 | Tokens out: 4200 | Tokens/sec: 49.7
#
# Scenario: Interactive Q&A (3 questions)
#   Avg latency: 18.6s | P95: 24.1s
#
# Saving results to benchmark_results.json
```

Results should be saved to `benchmark_results.json` in this directory when the
live benchmark path is implemented.

### 5. Risk Score Stability (`eval_risk_stability.py`)

Verifies that repeated analysis runs produce consistent risk scores.

```bash
python eval_risk_stability.py --portfolio-id p_demo --runs 5

# Expected output:
# AMD score variance across 5 runs: 1.2 (max delta: 1.8)
# PASS: all scores within ±3 of mean
```

## Fixtures

```
fixtures/
  labeled_queries.json   # planned retrieval queries, filters, and evidence hints
  known_changes.json     # planned disclosure-change targets and expected classes
```

The current fixtures are scaffolding for Kishan's retrieval/reranker work and
for later manual labeling. They do not require live Qdrant, live Gateway, or a
loaded demo database. Treat them as query/evidence targets until the real
ingestion smoke run produces stable chunk IDs and citation anchors.

Validate fixture shape without live services:

```bash
python -m pytest packages/evals/tests -x
```

## Future Running All Evals

```bash
pip install -r requirements.txt
python run_all_evals.py 2>&1 | tee eval_results.txt
```

`run_all_evals.py` is target tooling for the live retrieval pipeline. A citation
precision below 0.85 or retrieval recall below 0.70 should be fixed before a
live-ingestion demo.
