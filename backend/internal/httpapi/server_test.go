package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"fincontext/backend/internal/agent"
	"fincontext/backend/internal/citations"
	"fincontext/backend/internal/data"
	"fincontext/backend/internal/provider"
)

func TestHealthAndRunEndpoints(t *testing.T) {
	server := testServer(t)

	health := httptest.NewRecorder()
	server.ServeHTTP(health, httptest.NewRequest(http.MethodGet, "/api/health", nil))
	if health.Code != http.StatusOK {
		t.Fatalf("health code = %d", health.Code)
	}

	body := bytes.NewBufferString(`{"question":"What changed?"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/agent-runs", body)
	res := httptest.NewRecorder()
	server.ServeHTTP(res, req)
	if res.Code != http.StatusAccepted {
		t.Fatalf("start run code = %d body=%s", res.Code, res.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(res.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["id"] == "" {
		t.Fatal("expected run id")
	}
}

func TestDiffEndpoint(t *testing.T) {
	server := testServer(t)
	req := httptest.NewRequest(http.MethodGet, "/api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025", nil)
	res := httptest.NewRecorder()
	server.ServeHTTP(res, req)
	if res.Code != http.StatusOK {
		t.Fatalf("diff code = %d body=%s", res.Code, res.Body.String())
	}
}

func testServer(t *testing.T) *Server {
	t.Helper()
	store, err := data.Load("../../../data/fixtures")
	if err != nil {
		t.Fatal(err)
	}
	validator := citations.NewValidator(store)
	return New(store, agent.NewRunner(store, validator, nil), provider.NewFixtureProvider(store, validator), "", Dependencies{})
}
