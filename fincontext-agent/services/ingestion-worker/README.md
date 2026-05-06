# services/ingestion-worker

Python worker for SEC filing and transcript ingestion.

## Build Responsibilities

- Resolve ticker to CIK.
- Fetch filings.
- Parse HTML and PDF documents.
- Extract tables.
- Normalize sections.
- Create chunks and citation anchors.
- Generate embeddings.
- Upsert vector records.

## Suggested Stack

- Python 3.12.
- BeautifulSoup.
- lxml.
- PyMuPDF.
- pandas.
- LlamaIndex.
- sentence-transformers or Text Embeddings Inference.

## Key Files

```text
worker/
  main.py
  sec_client.py
  parsers/
    sec_html.py
    pdf.py
    tables.py
  chunking.py
  embeddings.py
  vector_store.py
  citations.py
```

