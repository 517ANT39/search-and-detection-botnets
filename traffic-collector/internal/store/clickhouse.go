package store

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"

	"traffic-collector/internal/config"
	"traffic-collector/internal/models"
)

// Store manages ClickHouse writes.
type Store struct {
	conn   clickhouse.Conn
	cfg    *config.Config
	pktCh  chan models.PacketRecord
	logger *slog.Logger
}

func New(cfg *config.Config, logger *slog.Logger) (*Store, error) {
	opts := &clickhouse.Options{
		Addr: cfg.ClickHouse.Addrs,
		Auth: clickhouse.Auth{
			Database: cfg.ClickHouse.Database,
			Username: cfg.ClickHouse.Username,
			Password: cfg.ClickHouse.Password,
		},
		DialTimeout:     cfg.ClickHouse.DialTimeout,
		MaxOpenConns:    cfg.ClickHouse.MaxOpenConns,
		MaxIdleConns:    cfg.ClickHouse.MaxIdleConns,
		ConnMaxLifetime: cfg.ClickHouse.ConnMaxLifetime,
		Settings: clickhouse.Settings{
			"max_execution_time": 60,
		},
	}

	conn, err := clickhouse.Open(opts)
	if err != nil {
		return nil, fmt.Errorf("clickhouse open: %w", err)
	}

	if err := conn.Ping(context.Background()); err != nil {
		return nil, fmt.Errorf("clickhouse ping: %w", err)
	}

	logger.Info("clickhouse connected", "addrs", cfg.ClickHouse.Addrs)

	chSize := cfg.Batch.ChannelSize
	if chSize <= 0 {
		chSize = 100000
	}

	return &Store{
		conn:   conn,
		cfg:    cfg,
		pktCh:  make(chan models.PacketRecord, chSize),
		logger: logger,
	}, nil
}

// Migrate runs CREATE TABLE IF NOT EXISTS.
func (s *Store) Migrate(ctx context.Context) error {
	return Migrate(ctx, s.conn)
}

// ── Host upsert (ReplacingMergeTree) ──────────────────────

func (s *Store) InsertHost(ctx context.Context, h *models.HostRecord) error {
	batch, err := s.conn.PrepareBatch(ctx, `
		INSERT INTO hosts (
			host_id, hostname, os, arch, kernel_version,
			interfaces, boot_time, registered_at
		)`)
	if err != nil {
		return fmt.Errorf("prepare host batch: %w", err)
	}

	if err := batch.Append(
		h.HostID,
		h.Hostname,
		h.OS,
		h.Arch,
		h.KernelVersion,
		h.Interfaces,
		h.BootTime,
		h.RegisteredAt,
	); err != nil {
		return fmt.Errorf("append host: %w", err)
	}

	return batch.Send()
}

// ── Packets — async batch pipeline ────────────────────────

// Enqueue adds packet records to the internal channel for async batch insert.
func (s *Store) Enqueue(records []models.PacketRecord) {
	for i := range records {
		select {
		case s.pktCh <- records[i]:
		default:
			s.logger.Warn("packet channel full, dropping")
			return
		}
	}
}

// RunBatchInsertLoop reads from pktCh, batches rows and inserts them.
// Blocks until ctx is cancelled.
func (s *Store) RunBatchInsertLoop(ctx context.Context, wg *sync.WaitGroup) {
	defer wg.Done()

	batchSize := s.cfg.Batch.Size
	if batchSize <= 0 {
		batchSize = 5000
	}
	flushInterval := s.cfg.Batch.FlushInterval
	if flushInterval <= 0 {
		flushInterval = 2 * time.Second
	}

	buf := make([]models.PacketRecord, 0, batchSize)
	ticker := time.NewTicker(flushInterval)
	defer ticker.Stop()

	flush := func() {
		if len(buf) == 0 {
			return
		}
		if err := s.insertPacketBatch(ctx, buf); err != nil {
			s.logger.Error("insert packets", "count", len(buf), "err", err)
		} else {
			s.logger.Debug("packets inserted", "count", len(buf))
		}
		buf = buf[:0]
	}

	for {
		select {
		case <-ctx.Done():
			flush()
			return

		case rec, ok := <-s.pktCh:
			if !ok {
				flush()
				return
			}
			buf = append(buf, rec)
			if len(buf) <= batchSize {
				flush()
			}

		case <-ticker.C:
			flush()
		}
	}
}

func (s *Store) insertPacketBatch(ctx context.Context, records []models.PacketRecord) error {
	batch, err := s.conn.PrepareBatch(ctx, `
		INSERT INTO packets (
			timestamp, host_id, src_ip, dst_ip,
			src_port, dst_port, pkt_len, protocol,
			hook_type, direction, if_index, received_at
		)`)
	if err != nil {
		return fmt.Errorf("prepare: %w", err)
	}

	for i := range records {
		r := &records[i]
		if err := batch.Append(
			r.Timestamp,
			r.HostID,
			r.SrcIP,
			r.DstIP,
			r.SrcPort,
			r.DstPort,
			r.PktLen,
			r.Protocol,
			r.HookType,
			r.Direction,
			r.IfIndex,
			r.ReceivedAt,
		); err != nil {
			_ = batch.Abort()
			return fmt.Errorf("append row %d: %w", i, err)
		}
	}

	return batch.Send()
}

// Close closes the ClickHouse connection.
func (s *Store) Close() error {
	close(s.pktCh)
	return s.conn.Close()
}

// Conn returns raw connection for use in migrations etc.
func (s *Store) Conn() driver.Conn {
	return s.conn
}
