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

	"monitoring-agent/internal/bpfprog"
	"monitoring-agent/internal/config"
	"monitoring-agent/internal/hostinfo"
	"monitoring-agent/internal/sender"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "path to config file")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config: %v\n", err)
		os.Exit(1)
	}

	logger := makeLogger(cfg.LogLevel)

	logger.Info("capture mode",
		"mode", cfg.Capture.Mode,
		"direction", cfg.Capture.Direction,
	)

	info, err := hostinfo.Collect(cfg)
	if err != nil {
		logger.Error("hostinfo", "err", err)
		os.Exit(1)
	}
	logger.Info("host",
		"id", info.HostID,
		"hostname", info.Hostname,
		"kernel", info.KernelVersion,
	)

	chSz := cfg.Batch.ChannelSize
	if chSz <= 0 {
		chSz = 8192
	}
	eventCh := make(chan bpfprog.RealPacketEvent, chSz) // ← RealPacketEvent

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	snd := sender.New(cfg, info, eventCh, logger)
	if err := snd.Connect(ctx); err != nil {
		logger.Error("grpc", "err", err)
		os.Exit(1)
	}
	defer snd.Close()

	coll := bpfprog.NewCollector(cfg, eventCh, logger)
	if err := coll.Load(); err != nil {
		logger.Error("ebpf load", "err", err)
		os.Exit(1)
	}
	defer coll.Close()

	if err := coll.Attach(); err != nil {
		logger.Error("ebpf attach", "err", err)
		os.Exit(1)
	}

	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		if err := coll.ReadLoop(ctx, &wg); err != nil {
			logger.Error("read loop", "err", err)
			cancel()
		}
	}()

	wg.Add(1)
	go snd.SendLoop(ctx, &wg)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh
	logger.Info("signal received, stopping", "sig", sig)
	cancel()
	wg.Wait()
	logger.Info("agent stopped")
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
