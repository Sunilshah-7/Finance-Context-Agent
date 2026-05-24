#!/usr/bin/env python3
"""Command-line wrapper for post-ingestion validation checks.

This script runs the validation helpers as one smoke command after the backend
has SQLite, Qdrant, and Gateway-backed ingestion data. It is safe to run with
``--skip-qdrant`` while Qdrant is offline, but full demo readiness should use
the Qdrant count check too.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence

from worker.validation import (
    inspect_citation_anchors,
    summarize_ingested_documents,
    validate_qdrant_count,
    validate_sqlite_fts,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate pre-ingested FinContext SQLite and Qdrant data."
    )
    parser.add_argument(
        "--db-path",
        default="../../fincontext.db",
        help="SQLite DB path. Defaults to ../../fincontext.db from this service.",
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant REST URL.",
    )
    parser.add_argument(
        "--qdrant-collection",
        default="fincontext_chunks",
        help="Qdrant collection name.",
    )
    parser.add_argument(
        "--qdrant-allowed-delta",
        type=int,
        default=0,
        help="Allowed absolute difference between SQLite chunks and Qdrant points.",
    )
    parser.add_argument(
        "--citation-sample-size",
        type=int,
        default=20,
        help="Number of SQLite chunk citation anchors to inspect.",
    )
    parser.add_argument(
        "--ticker",
        help="Optional ticker filter for document summaries.",
    )
    parser.add_argument(
        "--skip-qdrant",
        action="store_true",
        help="Skip Qdrant count validation when Qdrant is not running.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    conn = sqlite3.connect(args.db_path)
    failures: list[str] = []

    checks = [
        validate_sqlite_fts(conn),
        inspect_citation_anchors(conn, sample_size=args.citation_sample_size),
    ]
    if not args.skip_qdrant:
        checks.append(
            validate_qdrant_count(
                conn,
                qdrant_url=args.qdrant_url,
                collection=args.qdrant_collection,
                allowed_delta=args.qdrant_allowed_delta,
            )
        )

    for check in checks:
        print(check.message)
        if not check.ok:
            failures.append(check.message)

    summaries = summarize_ingested_documents(conn, ticker=args.ticker)
    if summaries:
        print("Documents:")
        for summary in summaries:
            sections = ",".join(summary.sections_parsed) or "-"
            print(
                f"- {summary.ticker} {summary.filing_type} {summary.filed_at}: "
                f"{summary.chunk_count} chunks; sections={sections}"
            )
    else:
        ticker_note = f" for {args.ticker.upper()}" if args.ticker else ""
        print(f"No ingested documents found{ticker_note}.")

    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
