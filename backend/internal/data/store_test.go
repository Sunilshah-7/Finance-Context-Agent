package data

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadValidatesFixtureStore(t *testing.T) {
	store, err := Load("../../../data/fixtures")
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if len(store.Evidence) == 0 {
		t.Fatal("expected evidence fixtures")
	}
	if _, ok := store.EvidenceByID("amd_2025_supply_chain"); !ok {
		t.Fatal("expected amd_2025_supply_chain citation")
	}
}

func TestLoadRejectsUnknownCitation(t *testing.T) {
	dir := t.TempDir()
	copyFixtures(t, "../../../data/fixtures", dir)
	if err := os.WriteFile(filepath.Join(dir, "memo.json"), []byte(`{
		"executive_summary":"bad",
		"exposure_affected":[],
		"top_changes":[{"ticker":"AMD","section":"Item 1A","summary":"bad","citation_ids":["missing"]}],
		"risk_scores":[],
		"watchlist":[],
		"limitations":"bad",
		"confidence":0.1,
		"citation_ids":["missing"],
		"disclaimer":"This output is research assistance only and does not constitute investment advice."
	}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(dir); err == nil {
		t.Fatal("expected unknown citation validation error")
	}
}

func copyFixtures(t *testing.T, src, dest string) {
	t.Helper()
	entries, err := os.ReadDir(src)
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		raw, err := os.ReadFile(filepath.Join(src, entry.Name()))
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dest, entry.Name()), raw, 0o644); err != nil {
			t.Fatal(err)
		}
	}
}
