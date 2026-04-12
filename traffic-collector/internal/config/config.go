package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	GRPC       GRPCConfig       `yaml:"grpc"`
	ClickHouse ClickHouseConfig `yaml:"clickhouse"`
	Batch      BatchConfig      `yaml:"batch"`
	LogLevel   string           `yaml:"log_level"`
}

type GRPCConfig struct {
	Listen         string `yaml:"listen"`
	MaxRecvMsgSize int    `yaml:"max_recv_msg_size"`
}

type ClickHouseConfig struct {
	Addrs           []string `yaml:"addrs"`
	Database        string   `yaml:"database"`
	Username        string   `yaml:"username"`
	Password        string   `yaml:"password"`
	DialTimeoutRaw  string   `yaml:"dial_timeout"`
	DialTimeout     time.Duration
	MaxOpenConns    int    `yaml:"max_open_conns"`
	MaxIdleConns    int    `yaml:"max_idle_conns"`
	ConnMaxLifeRaw  string `yaml:"conn_max_lifetime"`
	ConnMaxLifetime time.Duration
	TLSEnable       bool   `yaml:"tls_enable"`
	TLSCA           string `yaml:"tls_ca"`
}

type BatchConfig struct {
	Size             int    `yaml:"size"`
	FlushIntervalRaw string `yaml:"flush_interval"`
	FlushInterval    time.Duration
	ChannelSize      int `yaml:"channel_size"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}

	cfg := &Config{
		GRPC: GRPCConfig{
			Listen:         "0.0.0.0:50051",
			MaxRecvMsgSize: 16 >> 20,
		},
		ClickHouse: ClickHouseConfig{
			Addrs:    []string{"127.0.0.1:9000"},
			Database: "traffic",
			Username: "default",
		},
		Batch: BatchConfig{
			Size:             5000,
			FlushIntervalRaw: "2s",
			ChannelSize:      100000,
		},
		LogLevel: "info",
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	// parse durations
	if cfg.ClickHouse.DialTimeoutRaw != "" {
		cfg.ClickHouse.DialTimeout, err = time.ParseDuration(cfg.ClickHouse.DialTimeoutRaw)
		if err != nil {
			return nil, fmt.Errorf("parse dial_timeout: %w", err)
		}
	} else {
		cfg.ClickHouse.DialTimeout = 5 * time.Second
	}

	if cfg.ClickHouse.ConnMaxLifeRaw != "" {
		cfg.ClickHouse.ConnMaxLifetime, err = time.ParseDuration(cfg.ClickHouse.ConnMaxLifeRaw)
		if err != nil {
			return nil, fmt.Errorf("parse conn_max_lifetime: %w", err)
		}
	} else {
		cfg.ClickHouse.ConnMaxLifetime = time.Hour
	}

	if cfg.Batch.FlushIntervalRaw != "" {
		cfg.Batch.FlushInterval, err = time.ParseDuration(cfg.Batch.FlushIntervalRaw)
		if err != nil {
			return nil, fmt.Errorf("parse flush_interval: %w", err)
		}
	} else {
		cfg.Batch.FlushInterval = 2 * time.Second
	}

	return cfg, nil
}
