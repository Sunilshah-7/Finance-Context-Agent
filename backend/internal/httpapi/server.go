package httpapi

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"

	"fincontext/backend/internal/agent"
	"fincontext/backend/internal/data"
	"fincontext/backend/internal/provider"
)

type Server struct {
	router   chi.Router
	store    *data.Store
	runner   *agent.Runner
	provider provider.ChatProvider
	deps     Dependencies
}

type Dependencies struct {
	SQLite  HealthChecker
	Qdrant  HealthChecker
	Gateway HealthChecker
}

type HealthChecker interface {
	Health(ctx context.Context) error
}

func New(store *data.Store, runner *agent.Runner, chatProvider provider.ChatProvider, staticDir string, deps Dependencies) *Server {
	s := &Server{store: store, runner: runner, provider: chatProvider, deps: deps}
	r := chi.NewRouter()
	r.Use(cors)
	r.Get("/api/health", s.health)
	r.Get("/api/demo/portfolio", s.portfolio)
	r.Post("/api/agent-runs", s.startRun)
	r.Get("/api/agent-runs/{runID}", s.getRun)
	r.Get("/api/agent-runs/{runID}/events", s.runEvents)
	r.Get("/api/diff", s.diff)
	r.Post("/api/chat", s.chat)
	r.Get("/api/metrics", s.metrics)
	if staticDir != "" {
		r.Handle("/*", spa(staticDir))
	}
	s.router = r
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.router.ServeHTTP(w, r)
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	deps := map[string]string{}
	status := "ok"
	for name, checker := range map[string]HealthChecker{
		"sqlite":  s.deps.SQLite,
		"qdrant":  s.deps.Qdrant,
		"gateway": s.deps.Gateway,
	} {
		if checker == nil {
			deps[name] = "not_configured"
			continue
		}
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		err := checker.Health(ctx)
		cancel()
		if err != nil {
			status = "degraded"
			deps[name] = err.Error()
			continue
		}
		deps[name] = "ok"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":       status,
		"runtime":      "go",
		"fixture_mode": true,
		"evidence":     len(s.store.Evidence),
		"dependencies": deps,
		"disclaimer":   "research-assistance-only",
	})
}

func (s *Server) portfolio(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.store.Portfolio)
}

func (s *Server) startRun(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Question string `json:"question"`
	}
	_ = json.NewDecoder(r.Body).Decode(&req)
	if req.Question == "" {
		req.Question = "What changed in supply-chain or customer concentration risk for my semiconductor holdings?"
	}
	run := s.runner.Start(req.Question)
	writeJSON(w, http.StatusAccepted, run)
}

func (s *Server) getRun(w http.ResponseWriter, r *http.Request) {
	run, ok := s.runner.Get(chi.URLParam(r, "runID"))
	if !ok {
		writeError(w, http.StatusNotFound, "not_found", "agent run not found")
		return
	}
	writeJSON(w, http.StatusOK, run)
}

func (s *Server) runEvents(w http.ResponseWriter, r *http.Request) {
	runID := chi.URLParam(r, "runID")
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	flusher, ok := w.(http.Flusher)
	if !ok {
		writeError(w, http.StatusInternalServerError, "streaming_unavailable", "response writer does not support streaming")
		return
	}

	ticker := time.NewTicker(250 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case <-ticker.C:
			run, ok := s.runner.Get(runID)
			if !ok {
				fmt.Fprintf(w, "event: error\ndata: %s\n\n", `{"error":"agent run not found"}`)
				flusher.Flush()
				return
			}
			raw, _ := json.Marshal(run)
			fmt.Fprintf(w, "event: run\ndata: %s\n\n", raw)
			flusher.Flush()
			if run.Status == "completed" || run.Status == "failed" {
				return
			}
		}
	}
}

func (s *Server) diff(w http.ResponseWriter, r *http.Request) {
	fromYear, err := strconv.Atoi(r.URL.Query().Get("from"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_from_year", "from must be a year")
		return
	}
	toYear, err := strconv.Atoi(r.URL.Query().Get("to"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_to_year", "to must be a year")
		return
	}
	changes, err := s.store.Diff(r.URL.Query().Get("ticker"), r.URL.Query().Get("section"), fromYear, toYear)
	if err != nil {
		writeError(w, http.StatusNotFound, "diff_not_found", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"changes": changes})
}

func (s *Server) chat(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Question string `json:"question"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", "request body must be JSON")
		return
	}
	answer, err := s.provider.Answer(req.Question)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "citation_validation_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, answer)
}

func (s *Server) metrics(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.store.Metrics)
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		slog.Error("encode response", "error", err)
	}
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, map[string]any{
		"error": map[string]any{
			"code":      code,
			"message":   message,
			"retryable": false,
		},
	})
}

func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func spa(root string) http.Handler {
	fs := http.FileServer(http.Dir(root))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := filepath.Join(root, filepath.Clean(r.URL.Path))
		if info, err := os.Stat(path); err == nil && !info.IsDir() {
			fs.ServeHTTP(w, r)
			return
		}
		http.ServeFile(w, r, filepath.Join(root, "index.html"))
	})
}
