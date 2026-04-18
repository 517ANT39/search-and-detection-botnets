package bpfprog

import (
	"bytes"
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"log/slog"
	"sync"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/perf"

	"monitoring-agent/internal/config"
)

type PacketEvent = trafficPacketEvent

// RealPacketEvent — событие с реальным wall-clock временем.
type RealPacketEvent struct {
	PacketEvent
	RealTimestampNs int64 // Unix epoch nanoseconds
}

type Collector struct {
	cfg    *config.Config
	objs   trafficObjects
	reader *perf.Reader
	offset MonoOffset // ← смещение mono → realtime

	closers []func() error
	eventCh chan RealPacketEvent // ← теперь RealPacketEvent
	logger  *slog.Logger
}

func NewCollector(cfg *config.Config, evtCh chan RealPacketEvent, logger *slog.Logger) *Collector {
	return &Collector{
		cfg:     cfg,
		eventCh: evtCh,
		logger:  logger,
		offset:  NewMonoOffset(), // ← вычисляем при создании
	}
}

func (c *Collector) Load() error {
	spec, err := loadTraffic()
	if err != nil {
		return fmt.Errorf("load spec: %w", err)
	}

	if err := spec.LoadAndAssign(&c.objs, &ebpf.CollectionOptions{
		Programs: ebpf.ProgramOptions{
			LogLevel: ebpf.LogLevelInstruction,
		},
	}); err != nil {
		var ve *ebpf.VerifierError
		if errors.As(err, &ve) {
			c.logger.Error("verifier", "err", ve)
		}
		return fmt.Errorf("load objects: %w", err)
	}

	c.logger.Info("mono offset calculated",
		"offset_ms", c.offset.offsetNs/1e6,
	)

	return nil
}

func (c *Collector) Attach() error {
	mode := c.cfg.Capture.Mode
	dir := c.cfg.Capture.Direction

	switch mode {
	case config.ModeInterface:
		switch dir {
		case config.DirIngress:
			return c.attachXDP()
		case config.DirEgress:
			return c.attachTCEgress()
		case config.DirBoth:
			return c.attachTCBoth()
		}
	case config.ModeCgroup:
		return c.attachCgroup()
	}

	return fmt.Errorf("unsupported mode/direction: %s/%s", mode, dir)
}

func (c *Collector) ReadLoop(ctx context.Context, wg *sync.WaitGroup) error {
	defer wg.Done()

	perCPU := c.cfg.PerfPerCPUBuffer
	if perCPU <= 0 {
		perCPU = 65536
	}

	var err error
	c.reader, err = perf.NewReader(c.objs.Events, perCPU)
	if err != nil {
		return fmt.Errorf("new perf reader: %w", err)
	}

	go func() {
		<-ctx.Done()
		_ = c.reader.Close()
	}()

	c.logger.Info("perf read loop started")

	for {
		record, err := c.reader.Read()
		if err != nil {
			if errors.Is(err, perf.ErrClosed) {
				c.logger.Info("perf reader closed")
				return nil
			}
			c.logger.Warn("perf read", "err", err)
			continue
		}
		if record.LostSamples > 0 {
			c.logger.Warn("lost samples", "count", record.LostSamples)
			continue
		}

		var raw PacketEvent
		if err := binary.Read(
			bytes.NewReader(record.RawSample),
			binary.LittleEndian,
			&raw,
		); err != nil {
			c.logger.Warn("decode", "err", err)
			continue
		}

		// ── Конвертируем monotonic → realtime ──
		evt := RealPacketEvent{
			PacketEvent:     raw,
			RealTimestampNs: c.offset.ToRealtime(raw.TimestampNs),
		}

		select {
		case c.eventCh <- evt:
		default:
			c.logger.Debug("event channel full, dropping")
		}
	}
}

func (c *Collector) Close() {
	for i := len(c.closers) - 1; i >= 0; i-- {
		if err := c.closers[i](); err != nil {
			c.logger.Warn("close", "err", err)
		}
	}
	c.objs.Close()
}
