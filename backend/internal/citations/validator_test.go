package citations

import (
	"testing"

	"fincontext/backend/internal/data"
)

func TestValidatorRejectsUnsupportedCitation(t *testing.T) {
	store, err := data.Load("../../../data/fixtures")
	if err != nil {
		t.Fatal(err)
	}
	validator := NewValidator(store)
	if err := validator.ValidateIDs([]string{"amd_2025_supply_chain"}); err != nil {
		t.Fatalf("expected known citation to validate: %v", err)
	}
	if err := validator.ValidateIDs([]string{"not_real"}); err == nil {
		t.Fatal("expected unsupported citation error")
	}
}
