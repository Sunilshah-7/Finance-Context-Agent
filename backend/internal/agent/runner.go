package agent

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"log/slog"
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
	repo      RunRepository
}

type RunRepository interface {
	SaveRun(ctx context.Context, run domain.AgentRun) error
	GetRun(ctx context.Context, id string) (domain.AgentRun, bool, error)
}

func NewRunner(store *data.Store, validator citations.Validator, repo RunRepository) *Runner {
	return &Runner{store: store, validator: validator, runs: map[string]*domain.AgentRun{}, repo: repo}
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
	r.persist(*run)

	go r.execute(run.ID)
	return *run
}

func (r *Runner) Get(id string) (domain.AgentRun, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	run, ok := r.runs[id]
	if !ok {
		if r.repo != nil {
			run, found, err := r.repo.GetRun(context.Background(), id)
			if err != nil {
				slog.Warn("load persisted run", "run_id", id, "error", err)
				return domain.AgentRun{}, false
			}
			return run, found
		}
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
	r.persist(*run)
}

func (r *Runner) setStatus(id, status string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.runs[id].Status = status
	r.runs[id].UpdatedAt = time.Now().UTC()
	r.persistLocked(id)
}

func (r *Runner) startStage(id string, index int) {
	r.mu.Lock()
	defer r.mu.Unlock()
	now := time.Now().UTC()
	run := r.runs[id]
	run.Stages[index].Status = "running"
	run.Stages[index].StartedAt = &now
	run.UpdatedAt = now
	r.persistLocked(id)
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
	r.persistLocked(id)
}

func (r *Runner) persistLocked(id string) {
	if r.repo == nil {
		return
	}
	run, ok := r.runs[id]
	if !ok {
		return
	}
	if err := r.repo.SaveRun(context.Background(), *run); err != nil {
		slog.Warn("persist run", "run_id", id, "error", err)
	}
}

func (r *Runner) persist(run domain.AgentRun) {
	if r.repo == nil {
		return
	}
	if err := r.repo.SaveRun(context.Background(), run); err != nil {
		slog.Warn("persist run", "run_id", run.ID, "error", err)
	}
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
