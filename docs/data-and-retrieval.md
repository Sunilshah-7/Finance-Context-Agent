# Data and Retrieval

## Data Sources (MVP)

The MVP uses only free, publicly available sources:

| Source | What we get | Access method |
|--------|-------------|---------------|
| SEC EDGAR HTML filings | 10-K and 10-Q for all public companies | Direct EDGAR REST API, no key required |
| EDGAR company_tickers.json | Ticker → CIK mapping for all public companies | Single JSON file download, cache locally |
| EDGAR submissions API | Filing list per company | `https://data.sec.gov/submissions/CIK{cik}.json` |
| User portfolio CSV | Holdings: ticker, shares, market_value, sector | File upload via React UI |

**Not used in MVP:**
- PDF filings (too unreliable to parse quickly, not needed for HTML-available filings)
- Earnings transcripts (require licensing or scraping)
- Real-time market data (not needed — filing analysis is the product)
- XBRL structured data (useful but adds complexity; EDGAR HTML tables are sufficient for MVP)

## Demo Corpus (Pre-Ingested)

Pre-ingest these before the build phase starts. All 5 are in the demo seed portfolio.

| Ticker | CIK | Why included |
|--------|-----|-------------|
| AMD | 0000002488 | AMD judges love seeing their own filings analyzed |
| NVDA | 0001045810 | Direct AMD competitor, interesting for comparison |
| MSFT | 0000789019 | Large-cap tech, good for cross-sector balance |
| JPM | 0000019617 | Financials, different risk profile, diverse portfolio |
| TSLA | 0001318605 | High-disclosure-volatility company, good for diff demo |

For each ticker, ingest:
- 10-K: fiscal years 2022, 2023, 2024, 2025 (where filed)
- 10-Q: the 2 most recent quarterly filings

This gives 4 years of annual data for the disclosure diff feature and recent quarterly data for current state analysis.

## SEC EDGAR Rate Limits and Best Practices

- Maximum 10 requests/second to EDGAR APIs
- Must set `User-Agent: FinContextAgent/0.1 your-email@example.com` — EDGAR blocks requests without this
- Do not hammer the EDGAR filing document endpoint — use 0.1 second delay between requests
- Cache all downloaded HTML locally so re-runs don't re-download

EDGAR base URLs:
```
https://data.sec.gov/                     — structured data API (company info, submissions)
https://www.sec.gov/Archives/edgar/data/  — raw filing documents
https://efts.sec.gov/LATEST/search-edgar/ — full-text search (not needed for MVP)
```

Fetch a company's filing list:
```python
import httpx

async def get_filings(cik: str, form_type: str, user_agent: str) -> list[dict]:
    cik_padded = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    async with httpx.AsyncClient(headers={"User-Agent": user_agent}) as client:
        response = await client.get(url)
        data = response.json()

    filings = data["filings"]["recent"]
    results = []
    for i, form in enumerate(filings["form"]):
        if form == form_type:
            results.append({
                "accession_number": filings["accessionNumber"][i].replace("-", ""),
                "filed_at": filings["filingDate"][i],
                "primary_document": filings["primaryDocument"][i],
            })
    return results
```

Download a specific filing document:
```python
def build_filing_url(cik: str, accession_number: str, filename: str) -> str:
    cik_stripped = str(int(cik))  # remove leading zeros for archive path
    accession_dashed = f"{accession_number[:10]}-{accession_number[10:12]}-{accession_number[12:]}"
    return f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession_dashed}/{filename}"
```

## Document Normalization

All EDGAR HTML filings are normalized into this intermediate shape before chunking:

```python
class NormalizedDocument(BaseModel):
    document_id: str
    ticker: str
    cik: str
    filing_type: str           # "10-K", "10-Q", "8-K"
    accession_number: str
    filed_at: str              # ISO date "2025-02-14"
    fiscal_period: str         # "FY2024", "Q3-2024"
    source_url: str
    sections: list[NormalizedSection]

class NormalizedSection(BaseModel):
    section_id: str            # "item_1a", "item_7", etc.
    item_label: str            # "Item 1A", "Item 7"
    title: str                 # "Risk Factors", "MD&A"
    text: str                  # cleaned plain text of the section
    tables: list[str]          # extracted table texts (CSV or markdown format)
    word_count: int
```

## EDGAR HTML Section Detection

EDGAR HTML has several structural conventions depending on the filing year:

**Post-2018 EDGAR filings (most common now):**
- Sections are wrapped in `<div>` elements with `id` attributes matching the item label
- Example: `<div id="item1a"><h2>Item 1A. Risk Factors</h2>...`

**Pre-2018 EDGAR filings:**
- Sections are delimited by `<p>` or `<b>` tags containing the item label text
- No structured id attributes

**Detection strategy (handles both):**
```python
import re
from bs4 import BeautifulSoup

SECTION_LABELS = {
    "item_1":  r"item\s+1\.?\s*(business)?",
    "item_1a": r"item\s+1a\.?\s*(risk\s+factors)?",
    "item_7":  r"item\s+7\.?\s*(management.{0,30}discussion)?",
    "item_7a": r"item\s+7a\.?\s*(quantitative)?",
    "item_8":  r"item\s+8\.?\s*(financial\s+statements)?",
}

def find_sections(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")

    # Try id-attribute detection first (post-2018)
    sections = {}
    for section_id, pattern in SECTION_LABELS.items():
        el = soup.find(id=re.compile(pattern, re.IGNORECASE))
        if el:
            sections[section_id] = el.get_text(separator=" ")

    # Fallback: text-content detection
    if not sections:
        # Find all headings and look for item label patterns
        for heading in soup.find_all(["h1", "h2", "h3", "b", "p"]):
            text = heading.get_text().strip().lower()
            for section_id, pattern in SECTION_LABELS.items():
                if re.match(pattern, text, re.IGNORECASE) and section_id not in sections:
                    # Get sibling content until next heading
                    content = extract_until_next_heading(heading)
                    sections[section_id] = content

    return sections
```

## Chunking Rules

| Parameter | Value | Reason |
|-----------|-------|--------|
| Target chunk size | 600–1,000 tokens | Large enough for semantic coherence, small enough for precise retrieval |
| Overlap | 100 tokens | Preserve context at chunk boundaries for retrieval |
| Max chunk size | 1,200 tokens | Hard limit — anything larger loses retrieval precision |
| Min chunk size | 200 tokens | Discard tiny fragments that have no retrievable value |

Chunking uses a paragraph-aware splitter:
1. Split section text by double newlines (paragraph boundaries)
2. Accumulate paragraphs until chunk size is reached
3. When limit hit, save current chunk and start new chunk with last 100-token overlap
4. If a single paragraph exceeds the max chunk size, split at sentence boundary

Tables:
- Tables are never split across chunks
- Each table becomes its own chunk regardless of size
- Table citation anchor: `{ticker} {filing_type} {section_label} table {table_idx}`

Citation anchor format (strict, do not deviate):
```
{TICKER} {FILING_TYPE} {SECTION_LABEL} paragraph {N}
{TICKER} {FILING_TYPE} {SECTION_LABEL} table {N}
```
Examples:
```
AMD 10-K Item 1A paragraph 42
NVDA 10-Q Item 7 table 3
```

## Qdrant Collection Schema

Collection: `fincontext_chunks`
Vector dimensions: 1024
Distance: Cosine

Required payload for every point:
```python
{
    "chunk_id": str,          # UUID, matches SQLite chunks.id
    "document_id": str,       # UUID, matches SQLite documents.id
    "ticker": str,            # "AMD"
    "cik": str,               # "0000002488"
    "company_name": str,      # "Advanced Micro Devices, Inc."
    "filing_type": str,       # "10-K"
    "accession_number": str,  # raw accession number
    "filed_at": str,          # ISO date "2025-02-14"
    "fiscal_period": str,     # "FY2024"
    "section": str,           # "item_1a"
    "item_label": str,        # "Item 1A"
    "section_title": str,     # "Risk Factors"
    "chunk_index": int,       # 0-based index within document
    "token_count": int,       # approximate token count
    "text": str,              # full chunk text (stored in payload for reranker)
    "text_hash": str,         # SHA256[:16] for deduplication
    "citation_anchor": str,   # "AMD 10-K Item 1A paragraph 42"
    "source_url": str,        # full EDGAR document URL
    "is_table": bool,         # true if this chunk is a table
}
```

Qdrant indexes to create (for efficient payload filtering):
```python
client.create_payload_index("fincontext_chunks", "ticker", "keyword")
client.create_payload_index("fincontext_chunks", "filing_type", "keyword")
client.create_payload_index("fincontext_chunks", "filed_at", "keyword")
client.create_payload_index("fincontext_chunks", "section", "keyword")
```

## Embedding Models

Primary: `BAAI/bge-large-en-v1.5`
- Output dimensions: 1024
- Max input tokens: 512 (truncate at tokenizer level before sending)
- Normalize output vectors before storing in Qdrant (cosine similarity requires unit vectors)
- MTEB score: 0.639 retrieval (English), consistently top performer at this size

Fallback: `intfloat/e5-large-v2`
- Same dimensions (1024)
- Use if BGE-large has loading issues on ROCm

**Important:** BGE-large requires prepending `"Represent this sentence: "` to query text but NOT to document text. e5-large requires `"query: "` prefix for queries and `"passage: "` prefix for documents. Choose one model and stick with it for the entire ingestion run.

## Retrieval Implementation

### BM25 (SQLite FTS5)

```sql
-- Search query with ticker and filing type filter
SELECT
    c.id as chunk_id,
    c.citation_anchor,
    c.text,
    c.filed_at,
    c.source_url,
    bm25(chunks_fts, 1.0) as bm25_score
FROM chunks_fts
JOIN chunks c ON c.rowid = chunks_fts.rowid
WHERE chunks_fts MATCH :query
  AND chunks_fts.ticker = :ticker
  AND chunks_fts.filing_type IN (:filing_types)
ORDER BY bm25_score DESC
LIMIT 50;
```

BM25 excels for queries containing specific financial terms: "going concern", "covenant violation", "TSMC", "export controls", "customer concentration". Always run BM25 alongside vector search — do not use vector-only retrieval for financial text.

### Vector Search (Qdrant)

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, DatetimeRange

def build_filter(tickers, filing_types, date_from, date_to):
    conditions = [
        FieldCondition(key="ticker", match=MatchValue(value=ticker))
        for ticker in tickers
    ]
    return Filter(
        must=[
            Filter(should=conditions),  # any of the tickers
            FieldCondition(key="filing_type", match=MatchAny(any=filing_types)),
            FieldCondition(key="filed_at", range=Range(gte=date_from, lte=date_to)),
        ]
    )

results = client.search(
    collection_name="fincontext_chunks",
    query_vector=query_embedding,
    query_filter=build_filter(["AMD", "NVDA"], ["10-K", "10-Q"], "2023-01-01", "2026-05-06"),
    limit=50,
    with_payload=True,
)
```

### Reciprocal Rank Fusion

```python
def rrf_merge(
    bm25_results: list[dict],
    vector_results: list[dict],
    k: int = 60
) -> list[dict]:
    scores: dict[str, float] = {}
    all_chunks: dict[str, dict] = {}

    for rank, chunk in enumerate(bm25_results):
        cid = chunk["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        all_chunks[cid] = chunk

    for rank, chunk in enumerate(vector_results):
        cid = chunk["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        all_chunks[cid] = chunk

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [all_chunks[cid] for cid in sorted_ids]
```

### Section Diversity Filter

After reranking, apply this to avoid returning 12 chunks all from the same section:

```python
def apply_diversity_filter(
    chunks: list[EvidenceChunk],
    max_per_section: int = 3,
    total: int = 12
) -> list[EvidenceChunk]:
    section_counts: dict[str, int] = {}
    result = []
    for chunk in chunks:
        key = f"{chunk.ticker}:{chunk.section}"
        count = section_counts.get(key, 0)
        if count < max_per_section:
            result.append(chunk)
            section_counts[key] = count + 1
        if len(result) >= total:
            break
    return result
```

## Citation Format in UI

Display format in the React citation card:
```
[AMD 10-K · Item 1A · Risk Factors · filed 2025-02-14 · paragraph 42]
```

Full source metadata stored alongside each citation:
```json
{
  "citation_anchor": "AMD 10-K Item 1A paragraph 42",
  "source_url": "https://www.sec.gov/Archives/edgar/data/2488/000000248825000012/amd-2025.htm",
  "section": "Item 1A",
  "section_title": "Risk Factors",
  "filed_at": "2025-02-14",
  "fiscal_period": "FY2024",
  "chunk_id": "chunk_abc123"
}
```

Users can click a citation card to open the SEC EDGAR filing in a new browser tab at the correct URL.
