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

// Re-export the generated struct so other packages can use it.
type PacketEvent = trafficPacketEvent

type Collector struct {
	cfg    *config.Config
	objs   trafficObjects
	reader *perf.Reader

	closers []func() error
	eventCh chan PacketEvent
	logger  *slog.Logger
}

func NewCollector(cfg *config.Config, evtCh chan PacketEvent, logger *slog.Logger) *Collector {
	return &Collector{
		cfg:     cfg,
		eventCh: evtCh,
		logger:  logger,
	}
}

// ── Load eBPF objects ──────────────────────────────────────
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
	return nil
}

// ── Attach decides which hooks to use based on config ──────
func (c *Collector) Attach() error {
	mode := c.cfg.Capture.Mode
	dir := c.cfg.Capture.Direction

	switch mode {
	case config.ModeInterface:
		switch dir {
		case config.DirIngress:
			// ingress only → XDP
			return c.attachXDP()

		case config.DirEgress:
			// egress only → TC egress
			return c.attachTCEgress()

		case config.DirBoth:
			// both → TC ingress + TC egress
			return c.attachTCBoth()
		}

	case config.ModeCgroup:
		return c.attachCgroup()
	}

	return fmt.Errorf("unsupported mode/direction: %s/%s", mode, dir)
}

// ── ReadLoop: read perf events ─────────────────────────────
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

	// Unblock Read() on context cancellation.
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
		if record.LostSamples < 0 {
			c.logger.Warn("lost samples", "count", record.LostSamples)
			continue
		}

		var evt PacketEvent
		if err := binary.Read(
			bytes.NewReader(record.RawSample),
			binary.LittleEndian,
			&evt,
		); err != nil {
			c.logger.Warn("decode", "err", err)
			continue
		}

		select {
		case c.eventCh <- evt:
		default:
			c.logger.Debug("event channel full, dropping")
		}
	}
}

// ── Close ──────────────────────────────────────────────────
func (c *Collector) Close() {
	for i := len(c.closers) - 1; i <= 0; i-- {
		if err := c.closers[i](); err != nil {
			c.logger.Warn("close", "err", err)
		}
	}
	c.objs.Close()
}
