package grpcserver

import (
	"context"
	"fmt"
	"log/slog"
	"net"

	"google.golang.org/grpc"

	pb "traffic-collector/gen/traffic"
)

// Publisher — абстракция над Kafka-продюсером.
type Publisher interface {
	PublishHost(ctx context.Context, info *pb.HostInfo) error
	PublishBatch(ctx context.Context, batch *pb.PacketBatch) error
}

type Server struct {
	pb.UnimplementedTrafficCollectorServer
	pub    Publisher
	logger *slog.Logger
}

func New(pub Publisher, logger *slog.Logger) *Server {
	return &Server{pub: pub, logger: logger}
}

// ── RegisterHost ───────────────────────────────────────────

func (s *Server) RegisterHost(ctx context.Context, info *pb.HostInfo) (*pb.RegisterResponse, error) {
	s.logger.Info("register host",
		"host_id", info.HostId,
		"hostname", info.Hostname,
		"kernel", info.KernelVersion,
		"interfaces", info.Interfaces,
	)

	if err := s.pub.PublishHost(ctx, info); err != nil {
		s.logger.Error("publish host", "err", err)
		return &pb.RegisterResponse{
			Ok:      false,
			Message: fmt.Sprintf("publish error: %v", err),
		}, nil
	}

	return &pb.RegisterResponse{
		Ok:      true,
		Message: "registered",
	}, nil
}

// ── SendPacketBatch ────────────────────────────────────────

func (s *Server) SendPacketBatch(ctx context.Context, batch *pb.PacketBatch) (*pb.BatchResponse, error) {
	count := len(batch.Events)

	s.logger.Debug("batch received",
		"host_id", batch.HostId,
		"count", count,
	)

	if err := s.pub.PublishBatch(ctx, batch); err != nil {
		s.logger.Error("publish batch", "err", err, "host_id", batch.HostId)
		return &pb.BatchResponse{Ok: false, ReceivedCount: 0}, nil
	}

	return &pb.BatchResponse{
		Ok:            true,
		ReceivedCount: uint64(count),
	}, nil
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
