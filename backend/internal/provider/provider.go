package provider

import (
	"strings"

	"fincontext/backend/internal/citations"
	"fincontext/backend/internal/data"
	"fincontext/backend/internal/domain"
)

type ChatProvider interface {
	Answer(question string) (domain.ChatAnswer, error)
}

type FixtureProvider struct {
	store     *data.Store
	validator citations.Validator
}

func NewFixtureProvider(store *data.Store, validator citations.Validator) FixtureProvider {
	return FixtureProvider{store: store, validator: validator}
}

func (p FixtureProvider) Answer(question string) (domain.ChatAnswer, error) {
	ids := []string{"amd_2025_supply_chain", "amd_2025_export_controls"}
	text := "AMD's supply-chain risk reads higher because the newer disclosure is more specific about dependence on third-party manufacturers for advanced process nodes. The same evidence set also adds export-control exposure for AI accelerators, so the portfolio impact is concentrated in the semiconductor sleeve."
	if strings.Contains(strings.ToLower(question), "customer") {
		ids = append(ids, "nvda_2025_customer_concentration")
		text += " NVDA adds a related customer-concentration signal, which makes the semiconductor comparison useful rather than AMD-only."
	}
	cites, err := p.validator.Citations(ids)
	if err != nil {
		return domain.ChatAnswer{}, err
	}
	return domain.ChatAnswer{
		Answer:     text,
		Citations:  cites,
		Disclaimer: domain.ResearchDisclaimer,
	}, nil
}
