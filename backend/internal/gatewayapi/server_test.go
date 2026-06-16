package gatewayapi

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"fincontext/backend/internal/config"
)

func TestHealthReportsDegradedWithoutNIMKey(t *testing.T) {
	server := New(config.Gateway{Port: "8080"})
	res := httptest.NewRecorder()
	server.ServeHTTP(res, httptest.NewRequest(http.MethodGet, "/health", nil))
	if res.Code != http.StatusOK {
		t.Fatalf("health code = %d", res.Code)
	}
	if got := res.Body.String(); got == "" || !contains(got, "degraded") {
		t.Fatalf("expected degraded health, got %s", got)
	}
}

func TestChatRequiresNIMKey(t *testing.T) {
	server := New(config.Gateway{Port: "8080"})
	res := httptest.NewRecorder()
	server.ServeHTTP(res, httptest.NewRequest(http.MethodPost, "/v1/chat/completions", nil))
	if res.Code != http.StatusServiceUnavailable {
		t.Fatalf("chat code = %d", res.Code)
	}
}

func contains(s, needle string) bool {
	for i := 0; i+len(needle) <= len(s); i++ {
		if s[i:i+len(needle)] == needle {
			return true
		}
	}
	return false
}
