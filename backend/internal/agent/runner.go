package agent

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"sync"
	"time"

	"fincontext/backend/internal/citations"
	"fincontext/backend/internal/data"
	"fincontext/backend/internal/domain"
)

type Runner struct {
	store     *data.Store
	validator citations.Validator
	mu        sync.RWMutex
	runs      map[string]*domain.AgentRun
}

func NewRunner(store *data.Store, validator citations.Validator) *Runner {
	return &Runner{store: store, validator: validator, runs: map[string]*domain.AgentRun{}}
}

func (r *Runner) Start(question string) domain.AgentRun {
	now := time.Now().UTC()
	run := &domain.AgentRun{
		ID:        newID(),
		Status:    "queued",
		Question:  question,
		Stages:    initialStages(),
		Portfolio: r.store.Portfolio,
		Metrics:   r.store.Metrics,
		CreatedAt: now,
		UpdatedAt: now,
	}

	r.mu.Lock()
	r.runs[run.ID] = run
	r.mu.Unlock()

	go r.execute(run.ID)
	return *run
}

func (r *Runner) Get(id string) (domain.AgentRun, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	run, ok := r.runs[id]
	if !ok {
		return domain.AgentRun{}, false
	}
	return *run, true
}

func (r *Runner) execute(id string) {
	r.setStatus(id, "running")
	stageSummaries := []string{
		"Loaded the demo portfolio and identified semiconductor exposure.",
		"Selected citation-backed SEC evidence from the curated fixture store.",
		"Compared AMD and NVDA Item 1A language across filing years.",
		"Calculated holding-level risk scores and exposure impact.",
		"Rendered a citation-validated analyst memo.",
	}
	for i := range initialStages() {
		r.startStage(id, i)
		time.Sleep(350 * time.Millisecond)
		r.completeStage(id, i, stageSummaries[i])
	}

	r.mu.Lock()
	defer r.mu.Unlock()
	run := r.runs[id]
	if err := r.validator.ValidateMemo(r.store.Memo); err != nil {
		run.Status = "failed"
		run.Error = err.Error()
		run.UpdatedAt = time.Now().UTC()
		return
	}
	run.Status = "completed"
	run.RetrievedEvidence = r.store.Evidence
	run.DisclosureChanges = r.store.Changes
	run.RiskScores = r.store.Risks
	memo := r.store.Memo
	run.Memo = &memo
	run.UpdatedAt = time.Now().UTC()
}

func (r *Runner) setStatus(id, status string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.runs[id].Status = status
	r.runs[id].UpdatedAt = time.Now().UTC()
}

func (r *Runner) startStage(id string, index int) {
	r.mu.Lock()
	defer r.mu.Unlock()
	now := time.Now().UTC()
	run := r.runs[id]
	run.Stages[index].Status = "running"
	run.Stages[index].StartedAt = &now
	run.UpdatedAt = now
}

func (r *Runner) completeStage(id string, index int, summary string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	now := time.Now().UTC()
	run := r.runs[id]
	run.Stages[index].Status = "completed"
	run.Stages[index].CompletedAt = &now
	run.Stages[index].Summary = summary
	run.UpdatedAt = now
}

func initialStages() []domain.AgentStage {
	return []domain.AgentStage{
		{ID: "portfolio_context", Label: "Portfolio context", Status: "queued"},
		{ID: "evidence_retrieval", Label: "Evidence retrieval", Status: "queued"},
		{ID: "disclosure_diff", Label: "Disclosure diff", Status: "queued"},
		{ID: "risk_scoring", Label: "Risk scoring", Status: "queued"},
		{ID: "memo_generation", Label: "Memo generation", Status: "queued"},
	}
}

func newID() string {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		panic(errors.Join(errors.New("generate run id"), err))
	}
	return "run_" + hex.EncodeToString(b[:])
}
