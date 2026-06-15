package citations

import (
	"fmt"

	"fincontext/backend/internal/data"
	"fincontext/backend/internal/domain"
)

type Validator struct {
	store *data.Store
}

func NewValidator(store *data.Store) Validator {
	return Validator{store: store}
}

func (v Validator) ValidateIDs(ids []string) error {
	for _, id := range ids {
		if _, ok := v.store.EvidenceByID(id); !ok {
			return fmt.Errorf("unsupported citation id %q", id)
		}
	}
	return nil
}

func (v Validator) ValidateMemo(memo domain.AnalystMemo) error {
	if err := v.ValidateIDs(memo.CitationIDs); err != nil {
		return err
	}
	for _, change := range memo.TopChanges {
		if err := v.ValidateIDs(change.CitationIDs); err != nil {
			return err
		}
	}
	return nil
}

func (v Validator) Citations(ids []string) ([]domain.EvidenceCitation, error) {
	if err := v.ValidateIDs(ids); err != nil {
		return nil, err
	}
	return v.store.EvidenceFor(ids)
}
