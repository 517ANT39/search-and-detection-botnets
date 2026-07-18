package kafka

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"strconv"

	"github.com/segmentio/kafka-go"
	"google.golang.org/protobuf/proto"

	pb "traffic-collector/gen/traffic"
	"traffic-collector/internal/config"
)

// Producer публикует protobuf-сообщения в Kafka.
type Producer struct {
	writer       *kafka.Writer
	packetsTopic string
	hostsTopic   string
	logger       *slog.Logger
}

func NewProducer(cfg config.KafkaConfig, logger *slog.Logger) (*Producer, error) {
	if len(cfg.Brokers) == 0 {
		return nil, fmt.Errorf("kafka: no brokers configured")
	}

	w := &kafka.Writer{
		Addr:                   kafka.TCP(cfg.Brokers...),
		Balancer:               &kafka.Hash{}, // партиционирование по ключу (host_id)
		BatchSize:              cfg.BatchSize,
		BatchTimeout:           cfg.BatchTimeout,
		WriteTimeout:           cfg.WriteTimeout,
		RequiredAcks:           parseAcks(cfg.RequiredAcks),
		Compression:            parseCompression(cfg.Compression),
		Async:                  cfg.Async,
		AllowAutoTopicCreation: true, // создать топик при первой публикации, если его нет
	}

	if cfg.Async {
		w.Completion = func(msgs []kafka.Message, err error) {
			if err != nil {
				logger.Error("kafka async write failed", "err", err, "count", len(msgs))
			}
		}
	}

	return &Producer{
		writer:       w,
		packetsTopic: cfg.PacketsTopic,
		hostsTopic:   cfg.HostsTopic,
		logger:       logger,
	}, nil
}

// EnsureTopics явно создаёт необходимые топики, если они ещё не существуют.
// Идемпотентна: повторный вызов для существующего топика не вернёт ошибку.
func EnsureTopics(cfg config.KafkaConfig) error {
	if len(cfg.Brokers) == 0 {
		return fmt.Errorf("kafka: no brokers configured")
	}

	conn, err := kafka.Dial("tcp", cfg.Brokers[0])
	if err != nil {
		return fmt.Errorf("dial kafka: %w", err)
	}
	defer conn.Close()

	controller, err := conn.Controller()
	if err != nil {
		return fmt.Errorf("get controller: %w", err)
	}

	ctrlConn, err := kafka.Dial("tcp", net.JoinHostPort(controller.Host, strconv.Itoa(controller.Port)))
	if err != nil {
		return fmt.Errorf("dial controller: %w", err)
	}
	defer ctrlConn.Close()

	topics := []kafka.TopicConfig{
		{Topic: cfg.PacketsTopic, NumPartitions: 6, ReplicationFactor: 1},
		{Topic: cfg.HostsTopic, NumPartitions: 6, ReplicationFactor: 1},
	}

	if err := ctrlConn.CreateTopics(topics...); err != nil {
		return fmt.Errorf("create topics: %w", err)
	}
	return nil
}

// PublishHost сериализует HostInfo в protobuf и публикует в hosts-топик.
func (p *Producer) PublishHost(ctx context.Context, info *pb.HostInfo) error {
	payload, err := proto.Marshal(info)
	if err != nil {
		return fmt.Errorf("marshal HostInfo: %w", err)
	}

	msg := kafka.Message{
		Topic: p.hostsTopic,
		Key:   []byte(info.HostId),
		Value: payload,
	}

	if err := p.writer.WriteMessages(ctx, msg); err != nil {
		return fmt.Errorf("write host message: %w", err)
	}
	return nil
}

// PublishBatch публикует весь PacketBatch одним protobuf-сообщением.
// Ключ = host_id → все батчи одного хоста идут в одну партицию (порядок сохраняется).
func (p *Producer) PublishBatch(ctx context.Context, batch *pb.PacketBatch) error {
	if len(batch.Events) == 0 {
		return nil
	}

	payload, err := proto.Marshal(batch)
	if err != nil {
		return fmt.Errorf("marshal PacketBatch: %w", err)
	}

	msg := kafka.Message{
		Topic: p.packetsTopic,
		Key:   []byte(batch.HostId),
		Value: payload,
	}

	if err := p.writer.WriteMessages(ctx, msg); err != nil {
		return fmt.Errorf("write batch message: %w", err)
	}
	return nil
}

func (p *Producer) Close() error {
	return p.writer.Close()
}

func parseAcks(s string) kafka.RequiredAcks {
	switch s {
	case "none":
		return kafka.RequireNone
	case "all":
		return kafka.RequireAll
	default: // "one"
		return kafka.RequireOne
	}
}

func parseCompression(s string) kafka.Compression {
	switch s {
	case "gzip":
		return kafka.Gzip
	case "snappy":
		return kafka.Snappy
	case "lz4":
		return kafka.Lz4
	case "zstd":
		return kafka.Zstd
	default:
		return 0 // none
	}
}
