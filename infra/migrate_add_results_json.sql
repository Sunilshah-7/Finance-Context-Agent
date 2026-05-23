-- Migration: add results_json column to analysis_jobs
-- Run this once against any database created before this column was added to schema.sql.
-- Safe to run multiple times: the IF NOT EXISTS guard prevents errors on a fresh DB.
--
-- Usage:
--   sqlite3 fincontext.db < infra/migrate_add_results_json.sql
--
-- If you get "duplicate column name: results_json" you are already up to date.

ALTER TABLE analysis_jobs ADD COLUMN results_json TEXT;
-- stores the serialized AnalysisState JSON after the graph completes so that
-- GET /api/findings can return cached data without re-running the agent graph.
