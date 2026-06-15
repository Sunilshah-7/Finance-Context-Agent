package agent

import (
	"testing"
	"time"

	"fincontext/backend/internal/citations"
	"fincontext/backend/internal/data"
)

func TestRunnerCompletesDeterministicRun(t *testing.T) {
	store, err := data.Load("../../../data/fixtures")
	if err != nil {
		t.Fatal(err)
	}
	runner := NewRunner(store, citations.NewValidator(store))
	run := runner.Start("What changed?")

	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		current, ok := runner.Get(run.ID)
		if !ok {
			t.Fatal("run disappeared")
		}
		if current.Status == "completed" {
			if current.Memo == nil {
				t.Fatal("expected memo")
			}
			for _, stage := range current.Stages {
				if stage.Status != "completed" {
					t.Fatalf("stage %s status = %s", stage.ID, stage.Status)
				}
			}
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	t.Fatal("run did not complete")
}
