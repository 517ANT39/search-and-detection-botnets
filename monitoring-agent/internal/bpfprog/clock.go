package bpfprog

import (
	"time"

	"golang.org/x/sys/unix"
)

// MonoOffset — разница между wall-clock и монотонным временем.
// Прибавляется к bpf_ktime_get_ns() чтобы получить реальный timestamp.
type MonoOffset struct {
	offsetNs int64
}

// NewMonoOffset вычисляет смещение между CLOCK_REALTIME и CLOCK_MONOTONIC.
// Вызывается один раз при старте агента.
func NewMonoOffset() MonoOffset {
	// Берём оба значения максимально близко друг к другу
	var mono unix.Timespec
	if err := unix.ClockGettime(unix.CLOCK_MONOTONIC, &mono); err != nil {
		// fallback: грубое приближение
		return MonoOffset{offsetNs: time.Now().UnixNano()}
	}

	wall := time.Now().UnixNano()
	monoNs := mono.Sec*1e9 + mono.Nsec

	return MonoOffset{
		offsetNs: wall - monoNs,
	}
}

// ToRealtime конвертирует bpf_ktime_get_ns() в wall-clock наносекунды (Unix epoch).
func (o MonoOffset) ToRealtime(ktimeNs uint64) int64 {
	return int64(ktimeNs) + o.offsetNs
}

// ToTime конвертирует в time.Time.
func (o MonoOffset) ToTime(ktimeNs uint64) time.Time {
	return time.Unix(0, o.ToRealtime(ktimeNs))
}
