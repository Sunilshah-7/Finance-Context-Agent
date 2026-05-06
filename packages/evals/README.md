# packages/evals

Evaluation harness for retrieval quality, citation precision, disclosure diff accuracy, and AMD GPU performance benchmarks.

Run evals after the full pipeline is working (Day 7 in the milestone plan) and before demo polish. Eval results feed the AMD benchmark panel in the Gradio UI.

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

Fixtures: `fixtures/labeled_queries.json` — 20 queries with known relevant chunk IDs.
Build this fixture by manually searching EDGAR and labeling relevant paragraphs.

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

Fixtures: `fixtures/known_changes.json` — 10 manually verified disclosure changes with expected classifications.

### 4. Latency Benchmark (`eval_latency.py`)

Runs 5 benchmark scenarios and records AMD GPU performance metrics.

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

Results are saved to `benchmark_results.json` in this directory. The Agent API benchmark endpoint reads this file.

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
  labeled_queries.json   # [{query, expected_chunk_ids}] — for retrieval recall
  known_changes.json     # [{ticker, section, year_a, year_b, expected_change_type}] — for diff eval
```

Build fixtures manually using the pre-ingested data and actual EDGAR filings as ground truth.

## Running All Evals

```bash
pip install -r requirements.txt
python run_all_evals.py 2>&1 | tee eval_results.txt
```

`run_all_evals.py` runs all evals in sequence and prints a summary table. A citation precision below 0.85 or retrieval recall below 0.70 should be fixed before demo day.
