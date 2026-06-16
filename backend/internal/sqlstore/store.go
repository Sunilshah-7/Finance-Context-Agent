package sqlstore

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"fincontext/backend/internal/domain"
	_ "modernc.org/sqlite"
)

type Store struct {
	db *sql.DB
}

func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	store := &Store{db: db}
	if err := store.init(context.Background()); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) Health(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

func (s *Store) init(ctx context.Context) error {
	statements := []string{
		`PRAGMA journal_mode=WAL;`,
		`CREATE TABLE IF NOT EXISTS agent_runs (
			id TEXT PRIMARY KEY,
			status TEXT NOT NULL,
			question TEXT NOT NULL,
			payload_json TEXT NOT NULL,
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL
		);`,
		`CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);`,
		`CREATE TABLE IF NOT EXISTS portfolios (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			payload_json TEXT NOT NULL,
			updated_at TEXT NOT NULL
		);`,
		`CREATE TABLE IF NOT EXISTS evidence_citations (
			id TEXT PRIMARY KEY,
			ticker TEXT NOT NULL,
			anchor TEXT NOT NULL,
			payload_json TEXT NOT NULL
		);`,
	}
	for _, statement := range statements {
		if _, err := s.db.ExecContext(ctx, statement); err != nil {
			return err
		}
	}
	return nil
}

func (s *Store) SaveRun(ctx context.Context, run domain.AgentRun) error {
	raw, err := json.Marshal(run)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO agent_runs (id, status, question, payload_json, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
			status = excluded.status,
			question = excluded.question,
			payload_json = excluded.payload_json,
			updated_at = excluded.updated_at`,
		run.ID, run.Status, run.Question, string(raw), formatTime(run.CreatedAt), formatTime(run.UpdatedAt))
	return err
}

func (s *Store) GetRun(ctx context.Context, id string) (domain.AgentRun, bool, error) {
	var raw string
	err := s.db.QueryRowContext(ctx, `SELECT payload_json FROM agent_runs WHERE id = ?`, id).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return domain.AgentRun{}, false, nil
	}
	if err != nil {
		return domain.AgentRun{}, false, err
	}
	var run domain.AgentRun
	if err := json.Unmarshal([]byte(raw), &run); err != nil {
		return domain.AgentRun{}, false, err
	}
	return run, true, nil
}

func (s *Store) SeedFixtures(ctx context.Context, portfolio domain.Portfolio, evidence []domain.EvidenceCitation) error {
	rawPortfolio, err := json.Marshal(portfolio)
	if err != nil {
		return err
	}
	if _, err := s.db.ExecContext(ctx, `INSERT INTO portfolios (id, name, payload_json, updated_at)
		VALUES (?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET name = excluded.name, payload_json = excluded.payload_json, updated_at = excluded.updated_at`,
		portfolio.ID, portfolio.Name, string(rawPortfolio), formatTime(time.Now().UTC())); err != nil {
		return err
	}
	for _, citation := range evidence {
		rawCitation, err := json.Marshal(citation)
		if err != nil {
			return err
		}
		if _, err := s.db.ExecContext(ctx, `INSERT INTO evidence_citations (id, ticker, anchor, payload_json)
			VALUES (?, ?, ?, ?)
			ON CONFLICT(id) DO UPDATE SET ticker = excluded.ticker, anchor = excluded.anchor, payload_json = excluded.payload_json`,
			citation.ID, citation.Ticker, citation.Anchor, string(rawCitation)); err != nil {
			return fmt.Errorf("seed citation %s: %w", citation.ID, err)
		}
	}
	return nil
}

func formatTime(t time.Time) string {
	if t.IsZero() {
		t = time.Now().UTC()
	}
	return t.UTC().Format(time.RFC3339Nano)
}
