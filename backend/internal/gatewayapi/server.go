package gatewayapi

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"

	"fincontext/backend/internal/config"
)

type Server struct {
	router  chi.Router
	cfg     config.Gateway
	client  *http.Client
	metrics *Metrics
}

type Metrics struct {
	mu       sync.Mutex
	Requests map[string]int `json:"requests"`
	Errors   map[string]int `json:"errors"`
}

func New(cfg config.Gateway) *Server {
	s := &Server{
		cfg:     cfg,
		client:  &http.Client{Timeout: cfg.Timeout},
		metrics: &Metrics{Requests: map[string]int{}, Errors: map[string]int{}},
	}
	r := chi.NewRouter()
	r.Get("/health", s.health)
	r.Get("/metrics", s.getMetrics)
	r.Post("/v1/chat/completions", s.chatCompletions)
	r.Post("/v1/embeddings", s.proxyConfigured("embeddings", cfg.EmbeddingURL, "/v1/embeddings"))
	r.Post("/v1/rerank", s.proxyConfigured("rerank", cfg.RerankerURL, "/v1/rerank"))
	s.router = r
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.router.ServeHTTP(w, r)
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	upstreams := map[string]any{
		"nim_configured":       s.cfg.NIMAPIKey != "",
		"embedding_configured": s.cfg.EmbeddingURL != "",
		"reranker_configured":  s.cfg.RerankerURL != "",
		"planner_model":        s.cfg.NIMPlannerModel,
		"reasoner_model":       s.cfg.NIMReasonerModel,
	}
	status := "ok"
	if s.cfg.NIMAPIKey == "" {
		status = "degraded"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":    status,
		"provider":  "nvidia-nim",
		"upstreams": upstreams,
	})
}

func (s *Server) getMetrics(w http.ResponseWriter, r *http.Request) {
	s.metrics.mu.Lock()
	defer s.metrics.mu.Unlock()
	writeJSON(w, http.StatusOK, s.metrics)
}

func (s *Server) chatCompletions(w http.ResponseWriter, r *http.Request) {
	if s.cfg.NIMAPIKey == "" {
		s.record("chat", true)
		writeError(w, http.StatusServiceUnavailable, "nim_not_configured", "NIM_API_KEY is not configured")
		return
	}
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		writeError(w, http.StatusBadRequest, "read_body_failed", err.Error())
		return
	}
	var body map[string]any
	if err := json.Unmarshal(raw, &body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	body["model"] = s.routeModel(fmt.Sprint(body["model"]))
	rewritten, err := json.Marshal(body)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_payload", err.Error())
		return
	}
	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, strings.TrimRight(s.cfg.NIMBaseURL, "/")+"/chat/completions", bytes.NewReader(rewritten))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "request_create_failed", err.Error())
		return
	}
	req.Header.Set("Authorization", "Bearer "+s.cfg.NIMAPIKey)
	req.Header.Set("Content-Type", "application/json")
	s.proxy(w, req, "chat")
}

func (s *Server) proxyConfigured(name, upstream, path string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if upstream == "" {
			s.record(name, true)
			writeError(w, http.StatusServiceUnavailable, name+"_not_configured", strings.ToUpper(name)+" upstream is not configured")
			return
		}
		raw, err := io.ReadAll(r.Body)
		if err != nil {
			writeError(w, http.StatusBadRequest, "read_body_failed", err.Error())
			return
		}
		req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, strings.TrimRight(upstream, "/")+path, bytes.NewReader(raw))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "request_create_failed", err.Error())
			return
		}
		req.Header.Set("Content-Type", "application/json")
		s.proxy(w, req, name)
	}
}

func (s *Server) proxy(w http.ResponseWriter, req *http.Request, metric string) {
	start := time.Now()
	res, err := s.client.Do(req)
	if err != nil {
		s.record(metric, true)
		writeError(w, http.StatusBadGateway, "upstream_failed", err.Error())
		return
	}
	defer res.Body.Close()
	for key, values := range res.Header {
		for _, value := range values {
			w.Header().Add(key, value)
		}
	}
	w.WriteHeader(res.StatusCode)
	if _, err := io.Copy(w, res.Body); err != nil {
		slog.Warn("copy gateway response", "error", err)
	}
	s.record(metric, res.StatusCode >= 400)
	slog.Info("gateway request", "metric", metric, "status", res.StatusCode, "latency_ms", time.Since(start).Milliseconds())
}

func (s *Server) routeModel(model string) string {
	switch model {
	case "fincontext-planner":
		return s.cfg.NIMPlannerModel
	case "fincontext-reasoner":
		return s.cfg.NIMReasonerModel
	default:
		return model
	}
}

func (s *Server) record(metric string, failed bool) {
	s.metrics.mu.Lock()
	defer s.metrics.mu.Unlock()
	s.metrics.Requests[metric]++
	if failed {
		s.metrics.Errors[metric]++
	}
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, map[string]any{
		"error": map[string]any{
			"code":      code,
			"message":   message,
			"retryable": status >= 500,
		},
	})
}
