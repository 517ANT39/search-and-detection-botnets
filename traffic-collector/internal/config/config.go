package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	GRPC     GRPCConfig  `yaml:"grpc"`
	Kafka    KafkaConfig `yaml:"kafka"`
	LogLevel string      `yaml:"log_level"`
}

type GRPCConfig struct {
	Listen         string `yaml:"listen"`
	MaxRecvMsgSize int    `yaml:"max_recv_msg_size"`
}

type KafkaConfig struct {
	Brokers      []string `yaml:"brokers"`
	PacketsTopic string   `yaml:"packets_topic"`
	HostsTopic   string   `yaml:"hosts_topic"`

	BatchSize       int    `yaml:"batch_size"`
	BatchTimeoutRaw string `yaml:"batch_timeout"`
	BatchTimeout    time.Duration
	Compression     string `yaml:"compression"`   // none | gzip | snappy | lz4 | zstd
	RequiredAcks    string `yaml:"required_acks"` // none | one | all
	Async           bool   `yaml:"async"`
	WriteTimeoutRaw string `yaml:"write_timeout"`
	WriteTimeout    time.Duration
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}

	cfg := &Config{
		GRPC: GRPCConfig{
			Listen:         "0.0.0.0:50051",
			MaxRecvMsgSize: 16 << 20, // 16 MiB
		},
		Kafka: KafkaConfig{
			Brokers:         []string{"127.0.0.1:9092"},
			PacketsTopic:    "traffic.packets",
			HostsTopic:      "traffic.hosts",
			BatchSize:       5000,
			BatchTimeoutRaw: "1s",
			Compression:     "snappy",
			RequiredAcks:    "one",
			Async:           true,
			WriteTimeoutRaw: "10s",
		},
		LogLevel: "info",
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	if cfg.Kafka.BatchTimeoutRaw != "" {
		cfg.Kafka.BatchTimeout, err = time.ParseDuration(cfg.Kafka.BatchTimeoutRaw)
		if err != nil {
			return nil, fmt.Errorf("parse kafka batch_timeout: %w", err)
		}
	} else {
		cfg.Kafka.BatchTimeout = time.Second
	}

	if cfg.Kafka.WriteTimeoutRaw != "" {
		cfg.Kafka.WriteTimeout, err = time.ParseDuration(cfg.Kafka.WriteTimeoutRaw)
		if err != nil {
			return nil, fmt.Errorf("parse kafka write_timeout: %w", err)
		}
	} else {
		cfg.Kafka.WriteTimeout = 10 * time.Second
	}

	return cfg, nil
}
