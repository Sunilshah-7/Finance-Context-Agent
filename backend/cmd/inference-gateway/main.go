package main

import (
	"log/slog"
	"net/http"
	"os"
	"time"

	"fincontext/backend/internal/config"
	"fincontext/backend/internal/gatewayapi"
)

func main() {
	cfg := config.LoadGateway()
	server := &http.Server{
		Addr:              ":" + cfg.Port,
		Handler:           gatewayapi.New(cfg),
		ReadHeaderTimeout: 5 * time.Second,
	}
	slog.Info("starting inference gateway", "port", cfg.Port, "nim_base_url", cfg.NIMBaseURL)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		slog.Error("gateway stopped", "error", err)
		os.Exit(1)
	}
}
