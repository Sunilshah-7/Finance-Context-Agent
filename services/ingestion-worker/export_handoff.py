#!/usr/bin/env python3
"""CLI for exporting citation-ready ingestion samples for teammates.

Run this after SQLite ingestion has produced `documents` and `chunks` rows. It
does not call EDGAR, Gateway, Qdrant, or any model service; it only reads the
local metadata database and writes a JSON handoff file.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys

from worker.handoff_export import (
    DEFAULT_LIMIT,
    DEFAULT_PREVIEW_CHARS,
    HandoffFilters,
    build_handoff_export,
    parse_csv_filter,
    write_handoff_export,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export citation-ready ingestion chunks for retrieval/UI handoff."
    )
    parser.add_argument(
        "--db-path",
        default="../../fincontext.db",
        help="SQLite DB path. Defaults to ../../fincontext.db from this service.",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output JSON path. Use '-' for stdout. Defaults to stdout.",
    )
    parser.add_argument(
        "--tickers",
        help="Optional comma-separated ticker filter, for example AMD,NVDA.",
    )
    parser.add_argument(
        "--filing-types",
        help="Optional comma-separated filing type filter, for example 10-K,10-Q.",
    )
    parser.add_argument(
        "--sections",
        help="Optional comma-separated section filter, for example 'Item 1A,Item 7'.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum chunks to export. Defaults to {DEFAULT_LIMIT}.",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=DEFAULT_PREVIEW_CHARS,
        help=f"Text preview length per chunk. Defaults to {DEFAULT_PREVIEW_CHARS}.",
    )
    parser.add_argument(
        "--include-full-text",
        action="store_true",
        help="Include full chunk text in addition to text_preview.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit <= 0:
        print("error: --limit must be greater than zero", file=sys.stderr)
        return 2

    filters = HandoffFilters(
        tickers=parse_csv_filter(args.tickers),
        filing_types=parse_csv_filter(args.filing_types),
        sections=parse_csv_filter(args.sections),
        limit=args.limit,
        include_full_text=args.include_full_text,
        preview_chars=args.preview_chars,
    )

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(args.db_path)
        payload = build_handoff_export(conn, filters=filters)
        write_handoff_export(payload, args.output)
    except Exception as exc:  # noqa: BLE001 - CLI should report actionable errors
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
