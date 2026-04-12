package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"traffic-collector/internal/config"
	"traffic-collector/internal/grpcserver"
	"traffic-collector/internal/store"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "path to config")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config: %v\n", err)
		os.Exit(1)
	}

	logger := makeLogger(cfg.LogLevel)

	// ── ClickHouse ─────────────────────────────────────────
	st, err := store.New(cfg, logger)
	if err != nil {
		logger.Error("clickhouse connect", "err", err)
		os.Exit(1)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := st.Migrate(ctx); err != nil {
		logger.Error("migrate", "err", err)
		os.Exit(1)
	}
	logger.Info("clickhouse tables ready")

	// ── Batch insert loop ──────────────────────────────────
	var wg sync.WaitGroup

	wg.Add(1)
	go st.RunBatchInsertLoop(ctx, &wg)

	// ── gRPC server ────────────────────────────────────────
	srv := grpcserver.New(st, logger)
	gs, err := grpcserver.ListenAndServe(
		cfg.GRPC.Listen,
		cfg.GRPC.MaxRecvMsgSize,
		srv,
		logger,
	)
	if err != nil {
		logger.Error("grpc start", "err", err)
		os.Exit(1)
	}

	// ── Graceful shutdown ──────────────────────────────────
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh
	logger.Info("signal received", "sig", sig)

	// 1. Остановить приём новых gRPC запросов
	gs.GracefulStop()
	logger.Info("gRPC stopped")

	// 2. Остановить batch-loop (дождёмся flush остатков)
	cancel()
	wg.Wait()

	// 3. Закрыть ClickHouse
	if err := st.Close(); err != nil {
		logger.Warn("clickhouse close", "err", err)
	}

	logger.Info("collector stopped")
}

func makeLogger(level string) *slog.Logger {
	var lv slog.Level
	switch level {
	case "debug":
		lv = slog.LevelDebug
	case "warn":
		lv = slog.LevelWarn
	case "error":
		lv = slog.LevelError
	default:
		lv = slog.LevelInfo
	}
	return slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: lv}))
}
