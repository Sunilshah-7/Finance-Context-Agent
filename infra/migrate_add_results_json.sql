-- Migration: add results_json column to analysis_jobs
-- Run this once against any database created before this column was added to schema.sql.
-- Not idempotent: SQLite ALTER TABLE ADD COLUMN will error if the column already exists.
--
-- Usage:
--   sqlite3 fincontext.db < infra/migrate_add_results_json.sql
--
-- If you get "duplicate column name: results_json", the column is already present
-- and your database is up to date. No action needed.

ALTER TABLE analysis_jobs ADD COLUMN results_json TEXT;
-- stores the serialized AnalysisState JSON after the graph completes so that
-- GET /api/findings can return cached data without re-running the agent graph.
