package provider

import (
	"testing"

	"fincontext/backend/internal/citations"
	"fincontext/backend/internal/data"
)

func TestFixtureProviderReturnsValidatedCitations(t *testing.T) {
	store, err := data.Load("../../../data/fixtures")
	if err != nil {
		t.Fatal(err)
	}
	validator := citations.NewValidator(store)
	answer, err := NewFixtureProvider(store, validator).Answer("customer concentration")
	if err != nil {
		t.Fatal(err)
	}
	if len(answer.Citations) < 3 {
		t.Fatalf("expected customer-aware citations, got %d", len(answer.Citations))
	}
	for _, citation := range answer.Citations {
		if err := validator.ValidateIDs([]string{citation.ID}); err != nil {
			t.Fatal(err)
		}
	}
}
