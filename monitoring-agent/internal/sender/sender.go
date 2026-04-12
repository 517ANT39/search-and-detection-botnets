package sender

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "monitoring-agent/gen/traffic"
	"monitoring-agent/internal/bpfprog"
	"monitoring-agent/internal/config"
	"monitoring-agent/internal/hostinfo"
)

type Sender struct {
	cfg     *config.Config
	host    *hostinfo.Info
	conn    *grpc.ClientConn
	client  pb.TrafficCollectorClient
	eventCh chan bpfprog.PacketEvent
	logger  *slog.Logger
}

func New(
	cfg *config.Config,
	host *hostinfo.Info,
	evtCh chan bpfprog.PacketEvent,
	logger *slog.Logger,
) *Sender {
	return &Sender{cfg: cfg, host: host, eventCh: evtCh, logger: logger}
}

// Connect dials gRPC and sends RegisterHost.
func (s *Sender) Connect(ctx context.Context) error {
	var opts []grpc.DialOption
	if s.cfg.Server.Insecure {
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	}

	conn, err := grpc.NewClient(s.cfg.Server.Address, opts...)
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	s.conn = conn
	s.client = pb.NewTrafficCollectorClient(conn)

	resp, err := s.client.RegisterHost(ctx, &pb.HostInfo{
		HostId:        s.host.HostID,
		Hostname:      s.host.Hostname,
		Os:            s.host.OS,
		Arch:          s.host.Arch,
		KernelVersion: s.host.KernelVersion,
		Interfaces:    s.host.Interfaces,
		BootTimeSec:   s.host.BootTimeSec,
		RegisterTs:    s.host.RegisterTS,
	})
	if err != nil {
		return fmt.Errorf("register host: %w", err)
	}
	s.logger.Info("host registered", "ok", resp.Ok, "msg", resp.Message)
	return nil
}

// SendLoop batches events from the channel and ships them via gRPC.
func (s *Sender) SendLoop(ctx context.Context, wg *sync.WaitGroup) {
	defer wg.Done()

	batchSize := s.cfg.Batch.Size
	if batchSize <= 0 {
		batchSize = 256
	}
	flush := s.cfg.Batch.FlushInterval
	if flush <= 0 {
		flush = time.Second
	}

	buf := make([]*pb.PacketEvent, 0, batchSize)
	ticker := time.NewTicker(flush)
	defer ticker.Stop()

	send := func() {
		if len(buf) == 0 {
			return
		}
		s.sendBatch(ctx, buf)
		buf = make([]*pb.PacketEvent, 0, batchSize)
	}

	for {
		select {
		case <-ctx.Done():
			send()
			return

		case evt, ok := <-s.eventCh:
			if !ok {
				send()
				return
			}
			buf = append(buf, toPB(&evt))
			if len(buf) >= batchSize {
				send()
			}

		case <-ticker.C:
			send()
		}
	}
}

func (s *Sender) sendBatch(ctx context.Context, batch []*pb.PacketEvent) {
	ctx2, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	resp, err := s.client.SendPacketBatch(ctx2, &pb.PacketBatch{
		HostId:  s.host.HostID,
		BatchTs: time.Now().UnixNano(),
		Events:  batch,
	})
	if err != nil {
		s.logger.Warn("send batch", "count", len(batch), "err", err)
		return
	}
	s.logger.Debug("batch sent", "count", len(batch), "ack", resp.ReceivedCount)
}

func (s *Sender) Close() {
	if s.conn != nil {
		_ = s.conn.Close()
	}
}

func toPB(e *bpfprog.PacketEvent) *pb.PacketEvent {
	return &pb.PacketEvent{
		TimestampNs: e.TimestampNs,
		SrcIp:       e.SrcIp,
		DstIp:       e.DstIp,
		SrcPort:     uint32(e.SrcPort),
		DstPort:     uint32(e.DstPort),
		PktLen:      e.PktLen,
		Protocol:    uint32(e.Protocol),
		Hook:        pb.HookType(e.HookType),
		Direction:   pb.Direction(e.Direction),
		Ifindex:     e.Ifindex,
	}
}
