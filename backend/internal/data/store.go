package data

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"

	"fincontext/backend/internal/domain"
)

type Store struct {
	Portfolio domain.Portfolio
	Filings   []domain.Filing
	Evidence  []domain.EvidenceCitation
	Changes   []domain.DisclosureChange
	Risks     []domain.RiskScore
	Memo      domain.AnalystMemo
	Metrics   domain.Metrics

	evidenceByID map[string]domain.EvidenceCitation
}

func Load(dir string) (*Store, error) {
	s := &Store{}
	loaders := []struct {
		name string
		dest any
	}{
		{"portfolio.json", &s.Portfolio},
		{"filings.json", &s.Filings},
		{"evidence.json", &s.Evidence},
		{"disclosure_changes.json", &s.Changes},
		{"risk_scores.json", &s.Risks},
		{"memo.json", &s.Memo},
		{"metrics.json", &s.Metrics},
	}

	for _, loader := range loaders {
		if err := readJSON(filepath.Join(dir, loader.name), loader.dest); err != nil {
			return nil, err
		}
	}

	if s.Portfolio.Disclaimer == "" {
		s.Portfolio.Disclaimer = domain.ResearchDisclaimer
	}
	if s.Memo.Disclaimer == "" {
		s.Memo.Disclaimer = domain.ResearchDisclaimer
	}

	s.evidenceByID = make(map[string]domain.EvidenceCitation, len(s.Evidence))
	for _, ev := range s.Evidence {
		if ev.ID == "" {
			return nil, errors.New("evidence contains an empty id")
		}
		if _, exists := s.evidenceByID[ev.ID]; exists {
			return nil, fmt.Errorf("duplicate evidence id %q", ev.ID)
		}
		s.evidenceByID[ev.ID] = ev
	}

	if err := s.Validate(); err != nil {
		return nil, err
	}
	return s, nil
}

func readJSON(path string, dest any) error {
	raw, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read %s: %w", path, err)
	}
	if err := json.Unmarshal(raw, dest); err != nil {
		return fmt.Errorf("parse %s: %w", path, err)
	}
	return nil
}

func (s *Store) Validate() error {
	if len(s.Portfolio.Holdings) == 0 {
		return errors.New("portfolio has no holdings")
	}
	if !slices.ContainsFunc(s.Portfolio.Holdings, func(h domain.Holding) bool { return h.Ticker == "AMD" }) {
		return errors.New("required demo ticker AMD is missing from portfolio")
	}
	if !slices.ContainsFunc(s.Filings, func(f domain.Filing) bool {
		return f.Ticker == "AMD" && f.Section == "Item 1A"
	}) {
		return errors.New("required AMD Item 1A filing section is missing")
	}
	for _, change := range s.Changes {
		if len(change.CitationIDs) == 0 {
			return fmt.Errorf("change %s has no citations", change.ID)
		}
		if err := s.requireCitations("change "+change.ID, change.CitationIDs); err != nil {
			return err
		}
	}
	for _, risk := range s.Risks {
		for _, driver := range risk.Drivers {
			if err := s.requireCitations("risk "+risk.Ticker, driver.CitationIDs); err != nil {
				return err
			}
		}
	}
	for _, change := range s.Memo.TopChanges {
		if err := s.requireCitations("memo change "+change.Ticker, change.CitationIDs); err != nil {
			return err
		}
	}
	if err := s.requireCitations("memo evidence table", s.Memo.CitationIDs); err != nil {
		return err
	}
	return nil
}

func (s *Store) requireCitations(context string, ids []string) error {
	for _, id := range ids {
		if _, ok := s.evidenceByID[id]; !ok {
			return fmt.Errorf("%s references unknown citation %q", context, id)
		}
	}
	return nil
}

func (s *Store) EvidenceByID(id string) (domain.EvidenceCitation, bool) {
	ev, ok := s.evidenceByID[id]
	return ev, ok
}

func (s *Store) EvidenceFor(ids []string) ([]domain.EvidenceCitation, error) {
	result := make([]domain.EvidenceCitation, 0, len(ids))
	for _, id := range ids {
		ev, ok := s.EvidenceByID(id)
		if !ok {
			return nil, fmt.Errorf("unknown citation %q", id)
		}
		result = append(result, ev)
	}
	return result, nil
}

func (s *Store) Diff(ticker, section string, fromYear, toYear int) ([]domain.DisclosureChange, error) {
	var result []domain.DisclosureChange
	for _, change := range s.Changes {
		if change.Ticker == ticker && change.Section == section && change.FromYear == fromYear && change.ToYear == toYear {
			result = append(result, change)
		}
	}
	if len(result) == 0 {
		return nil, fmt.Errorf("no diff found for %s %s %d-%d", ticker, section, fromYear, toYear)
	}
	return result, nil
}
