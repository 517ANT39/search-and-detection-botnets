package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Direction constants used throughout the agent.
const (
	DirIngress = "ingress"
	DirEgress  = "egress"
	DirBoth    = "both"
)

// Mode constants.
const (
	ModeInterface = "interface"
	ModeCgroup    = "cgroup"
)

type Config struct {
	HostID     string `yaml:"host_id"`
	HostIDFile string `yaml:"host_id_file"`

	Server  ServerConfig  `yaml:"server"`
	Capture CaptureConfig `yaml:"capture"`
	Batch   BatchConfig   `yaml:"batch"`

	PerfPerCPUBuffer int    `yaml:"perf_per_cpu_buffer"`
	LogLevel         string `yaml:"log_level"`
}

type ServerConfig struct {
	Address  string `yaml:"address"`
	Insecure bool   `yaml:"insecure"`
	TLSCert  string `yaml:"tls_cert"`
	TLSKey   string `yaml:"tls_key"`
	TLSCA    string `yaml:"tls_ca"`
}

type CaptureConfig struct {
	Mode       string   `yaml:"mode"`      // "interface" | "cgroup"
	Direction  string   `yaml:"direction"` // "ingress" | "egress" | "both"
	Interfaces []string `yaml:"interfaces"`
	XDPFlags   uint32   `yaml:"xdp_flags"`
	CgroupPath string   `yaml:"cgroup_path"`
}

type BatchConfig struct {
	Size          int           `yaml:"size"`
	FlushInterval time.Duration `yaml:"-"`
	FlushRaw      string        `yaml:"flush_interval"`
	ChannelSize   int           `yaml:"channel_size"`
}

func (c *Config) Validate() error {
	switch c.Capture.Mode {
	case ModeInterface:
		if len(c.Capture.Interfaces) == 0 {
			return fmt.Errorf("mode=interface requires at least one interface")
		}
	case ModeCgroup:
		if c.Capture.CgroupPath == "" {
			return fmt.Errorf("mode=cgroup requires cgroup_path")
		}
	default:
		return fmt.Errorf("unknown mode %q (use 'interface' or 'cgroup')", c.Capture.Mode)
	}

	switch c.Capture.Direction {
	case DirIngress, DirEgress, DirBoth:
	default:
		return fmt.Errorf("unknown direction %q (use 'ingress', 'egress' or 'both')", c.Capture.Direction)
	}
	return nil
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config %s: %w", path, err)
	}

	cfg := &Config{
		HostIDFile:       "/var/lib/monitoring-agent/host_id",
		Server:           ServerConfig{Address: "127.0.0.1:50051", Insecure: true},
		Capture:          CaptureConfig{Mode: ModeInterface, Direction: DirBoth},
		Batch:            BatchConfig{Size: 256, FlushRaw: "1s", ChannelSize: 8192},
		PerfPerCPUBuffer: 65536,
		LogLevel:         "info",
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	// parse duration
	if cfg.Batch.FlushRaw != "" {
		d, err := time.ParseDuration(cfg.Batch.FlushRaw)
		if err != nil {
			return nil, fmt.Errorf("parse flush_interval: %w", err)
		}
		cfg.Batch.FlushInterval = d
	} else {
		cfg.Batch.FlushInterval = time.Second
	}

	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	return cfg, nil
}
