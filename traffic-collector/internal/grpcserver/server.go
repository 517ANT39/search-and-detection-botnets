package grpcserver

import (
	"context"
	"encoding/binary"
	"fmt"
	"log/slog"
	"net"
	"time"

	"google.golang.org/grpc"

	pb "traffic-collector/gen/traffic"
	"traffic-collector/internal/models"
	"traffic-collector/internal/store"
)

type Server struct {
	pb.UnimplementedTrafficCollectorServer
	store  *store.Store
	logger *slog.Logger
}

func New(st *store.Store, logger *slog.Logger) *Server {
	return &Server{store: st, logger: logger}
}

// ── RegisterHost ───────────────────────────────────────────

func (s *Server) RegisterHost(ctx context.Context, info *pb.HostInfo) (*pb.RegisterResponse, error) {
	s.logger.Info("register host",
		"host_id", info.HostId,
		"hostname", info.Hostname,
		"kernel", info.KernelVersion,
		"interfaces", info.Interfaces,
	)

	rec := &models.HostRecord{
		HostID:        info.HostId,
		Hostname:      info.Hostname,
		OS:            info.Os,
		Arch:          info.Arch,
		KernelVersion: info.KernelVersion,
		Interfaces:    info.Interfaces,
		BootTime:      time.Unix(info.BootTimeSec, 0),
		RegisteredAt:  time.Unix(0, info.RegisterTs),
	}

	if err := s.store.InsertHost(ctx, rec); err != nil {
		s.logger.Error("insert host", "err", err)
		return &pb.RegisterResponse{
			Ok:      false,
			Message: fmt.Sprintf("store error: %v", err),
		}, nil
	}

	return &pb.RegisterResponse{
		Ok:      true,
		Message: "registered",
	}, nil
}

// ── SendPacketBatch ────────────────────────────────────────

func (s *Server) SendPacketBatch(_ context.Context, batch *pb.PacketBatch) (*pb.BatchResponse, error) {
	now := time.Now()
	count := len(batch.Events)

	s.logger.Debug("batch received",
		"host_id", batch.HostId,
		"count", count,
	)

	records := make([]models.PacketRecord, 0, count)
	for _, evt := range batch.Events {
		records = append(records, models.PacketRecord{
			Timestamp:  time.Unix(0, int64(evt.TimestampNs)),
			HostID:     batch.HostId,
			SrcIP:      uint32ToIP(evt.SrcIp),
			DstIP:      uint32ToIP(evt.DstIp),
			SrcPort:    uint16(evt.SrcPort),
			DstPort:    uint16(evt.DstPort),
			PktLen:     evt.PktLen,
			Protocol:   uint8(evt.Protocol),
			HookType:   uint8(evt.Hook),
			Direction:  uint8(evt.Direction),
			IfIndex:    evt.Ifindex,
			ReceivedAt: now,
		})
	}

	// Async enqueue — неблокирующая запись
	s.store.Enqueue(records)

	return &pb.BatchResponse{
		Ok:            true,
		ReceivedCount: uint64(count),
	}, nil
}

// uint32 (little-endian from eBPF) → net.IP
func uint32ToIP(v uint32) net.IP {
	ip := make(net.IP, 4)
	binary.LittleEndian.PutUint32(ip, v)
	return ip
}

// ── Start gRPC listener ────────────────────────────────────

func ListenAndServe(addr string, maxRecvSize int, srv *Server, logger *slog.Logger) (*grpc.Server, error) {
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, fmt.Errorf("listen %s: %w", addr, err)
	}

	opts := []grpc.ServerOption{}
	if maxRecvSize > 0 {
		opts = append(opts, grpc.MaxRecvMsgSize(maxRecvSize))
	}

	gs := grpc.NewServer(opts...)
	pb.RegisterTrafficCollectorServer(gs, srv)

	go func() {
		logger.Info("gRPC server listening", "addr", addr)
		if err := gs.Serve(lis); err != nil {
			logger.Error("gRPC serve", "err", err)
		}
	}()

	return gs, nil
}
