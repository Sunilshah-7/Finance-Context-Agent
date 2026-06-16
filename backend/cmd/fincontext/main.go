package main

import (
	"log/slog"
	"net/http"
	"os"
	"time"

	"fincontext/backend/internal/agent"
	"fincontext/backend/internal/citations"
	"fincontext/backend/internal/data"
	"fincontext/backend/internal/httpapi"
	"fincontext/backend/internal/provider"
)

func main() {
	fixturesDir := env("FIXTURE_DIR", "data/fixtures")
	staticDir := os.Getenv("STATIC_DIR")
	port := env("PORT", "8080")

	store, err := data.Load(fixturesDir)
	if err != nil {
		slog.Error("load fixtures", "error", err)
		os.Exit(1)
	}
	validator := citations.NewValidator(store)
	runner := agent.NewRunner(store, validator, nil)
	chatProvider := provider.NewFixtureProvider(store, validator)
	server := httpapi.New(store, runner, chatProvider, staticDir, httpapi.Dependencies{})

	httpServer := &http.Server{
		Addr:              ":" + port,
		Handler:           server,
		ReadHeaderTimeout: 5 * time.Second,
	}

	slog.Info("starting fincontext", "port", port, "fixtures", fixturesDir, "static_dir", staticDir)
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		slog.Error("server stopped", "error", err)
		os.Exit(1)
	}
}

func env(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
