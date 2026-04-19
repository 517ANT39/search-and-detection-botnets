package models

import (
	"net"
	"time"
)

// HostRecord — строка в таблице hosts.
type HostRecord struct {
	HostID        string
	Hostname      string
	OS            string
	Arch          string
	KernelVersion string
	Interfaces    map[uint32]string
	BootTime      time.Time
	RegisteredAt  time.Time
}

// PacketRecord — строка в таблице packets.
type PacketRecord struct {
	Timestamp  time.Time
	HostID     string
	SrcIP      net.IP
	DstIP      net.IP
	SrcPort    uint16
	DstPort    uint16
	PktLen     uint32
	Protocol   uint8
	HookType   uint8
	Direction  uint8
	IfIndex    uint32
	ReceivedAt time.Time
}
