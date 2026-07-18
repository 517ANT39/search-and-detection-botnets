package main

import (
	"context"
	"flag"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"traffic-collector/internal/config"
	"traffic-collector/internal/grpcserver"
	"traffic-collector/internal/kafka"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "path to config file")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		slog.Error("load config", "err", err)
		os.Exit(1)
	}

	logger := newLogger(cfg.LogLevel)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// Явно создаём топики до старта, чтобы не ловить Unknown Topic Or Partition.
	if err := kafka.EnsureTopics(cfg.Kafka); err != nil {
		logger.Error("ensure kafka topics", "err", err)
		os.Exit(1)
	}

	producer, err := kafka.NewProducer(cfg.Kafka, logger)
	if err != nil {
		logger.Error("init kafka producer", "err", err)
		os.Exit(1)
	}

	srv := grpcserver.New(producer, logger)
	gs, err := grpcserver.ListenAndServe(cfg.GRPC.Listen, cfg.GRPC.MaxRecvMsgSize, srv, logger)
	if err != nil {
		logger.Error("start grpc", "err", err)
		os.Exit(1)
	}

	logger.Info("collector started",
		"grpc", cfg.GRPC.Listen,
		"brokers", cfg.Kafka.Brokers,
		"packets_topic", cfg.Kafka.PacketsTopic,
		"hosts_topic", cfg.Kafka.HostsTopic,
	)

	<-ctx.Done()
	logger.Info("shutting down")

	gs.GracefulStop()
	if err := producer.Close(); err != nil {
		logger.Error("close kafka producer", "err", err)
	}
}

func newLogger(level string) *slog.Logger {
	var lvl slog.Level
	switch level {
	case "debug":
		lvl = slog.LevelDebug
	case "warn":
		lvl = slog.LevelWarn
	case "error":
		lvl = slog.LevelError
	default:
		lvl = slog.LevelInfo
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: lvl}))
}
