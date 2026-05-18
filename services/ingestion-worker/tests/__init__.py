"""Tests for the ingestion worker.

These tests use mocked HTTP, small SEC-like HTML snippets, and temporary SQLite
databases so the foundation can be checked without live EDGAR, Gateway, or
Qdrant services.
"""
