package sqlstore

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"fincontext/backend/internal/domain"
)

func TestSaveAndLoadRun(t *testing.T) {
	store, err := Open(filepath.Join(t.TempDir(), "fincontext.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()

	run := domain.AgentRun{
		ID:        "run_test",
		Status:    "completed",
		Question:  "What changed?",
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}
	if err := store.SaveRun(context.Background(), run); err != nil {
		t.Fatal(err)
	}
	loaded, ok, err := store.GetRun(context.Background(), run.ID)
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Fatal("expected persisted run")
	}
	if loaded.ID != run.ID || loaded.Status != run.Status {
		t.Fatalf("loaded run mismatch: %+v", loaded)
	}
}

func TestSeedFixtures(t *testing.T) {
	store, err := Open(filepath.Join(t.TempDir(), "fincontext.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()

	portfolio := domain.Portfolio{ID: "p1", Name: "Demo"}
	evidence := []domain.EvidenceCitation{{ID: "c1", Ticker: "AMD", Anchor: "AMD 10-K Item 1A paragraph 1"}}
	if err := store.SeedFixtures(context.Background(), portfolio, evidence); err != nil {
		t.Fatal(err)
	}
}
