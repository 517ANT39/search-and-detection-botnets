package hostinfo

import (
	"fmt"
	"net"
	"os"
	"runtime"
	"strings"
	"time"

	"monitoring-agent/internal/config"

	"github.com/google/uuid"
)

type Info struct {
	HostID        string
	Hostname      string
	OS            string
	Arch          string
	KernelVersion string
	Interfaces    []string
	BootTimeSec   int64
	RegisterTS    int64
}

func Collect(cfg *config.Config) (*Info, error) {
	hostID, err := resolveHostID(cfg.HostID, cfg.HostIDFile)
	if err != nil {
		return nil, err
	}

	hostname, _ := os.Hostname()
	kernel := readLine("/proc/sys/kernel/osrelease")
	bootTime := readBootTime()

	activeIfaces := getActiveInterfaces()

	return &Info{
		HostID:        hostID,
		Hostname:      hostname,
		OS:            runtime.GOOS,
		Arch:          runtime.GOARCH,
		KernelVersion: kernel,
		Interfaces:    activeIfaces,
		BootTimeSec:   bootTime,
		RegisterTS:    time.Now().UnixNano(),
	}, nil
}
func getActiveInterfaces() []string {
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil
	}

	var active []string
	for _, iface := range ifaces {
		// Пропускаем loopback
		if iface.Flags&net.FlagLoopback != 0 {
			continue
		}

		// Пропускаем интерфейсы без флага UP
		if iface.Flags&net.FlagUp == 0 {
			continue
		}

		// Проверяем наличие хотя бы одного IP-адреса
		addrs, err := iface.Addrs()
		if err != nil || len(addrs) == 0 {
			continue
		}

		// Проверяем что есть хотя бы один не-link-local адрес
		hasUsableAddr := false
		for _, addr := range addrs {
			ip, _, err := net.ParseCIDR(addr.String())
			if err != nil {
				continue
			}
			// Пропускаем link-local (fe80::, 169.254.x.x)
			if ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() {
				continue
			}
			hasUsableAddr = true
			break
		}

		if hasUsableAddr {
			active = append(active, iface.Name)
		}
	}

	return active
}

func resolveHostID(explicit, file string) (string, error) {
	if explicit != "" {
		return explicit, nil
	}
	if data, err := os.ReadFile(file); err == nil {
		if id := strings.TrimSpace(string(data)); id != "" {
			return id, nil
		}
	}
	id := uuid.New().String()
	if dir := dirOf(file); dir != "" {
		if err := os.MkdirAll(dir, 0o755); err == nil {
			_ = os.WriteFile(file, []byte(id), 0o644)
		}
	}
	return id, nil
}

func dirOf(path string) string {
	for i := len(path) - 1; i >= 0; i-- {
		if path[i] == '/' {
			return path[:i]
		}
	}
	return ""
}

func readLine(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(data))
}

func readBootTime() int64 {
	data, err := os.ReadFile("/proc/stat")
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "btime ") {
			var bt int64
			fmt.Sscanf(line, "btime %d", &bt)
			return bt
		}
	}
	return 0
}
