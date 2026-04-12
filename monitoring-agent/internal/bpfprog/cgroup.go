package bpfprog

import (
	"fmt"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"

	"monitoring-agent/internal/config"
)

func (c *Collector) attachCgroup() error {
	cgPath := c.cfg.Capture.CgroupPath
	dir := c.cfg.Capture.Direction

	if dir == config.DirIngress || dir == config.DirBoth {
		l, err := link.AttachCgroup(link.CgroupOptions{
			Path:    cgPath,
			Attach:  ebpf.AttachCGroupInetIngress,
			Program: c.objs.CgSkbIngress,
		})
		if err != nil {
			return fmt.Errorf("cgroup ingress: %w", err)
		}
		c.closers = append(c.closers, l.Close)
		c.logger.Info("cgroup_skb/ingress attached", "path", cgPath)
	}

	if dir == config.DirEgress || dir == config.DirBoth {
		l, err := link.AttachCgroup(link.CgroupOptions{
			Path:    cgPath,
			Attach:  ebpf.AttachCGroupInetEgress,
			Program: c.objs.CgSkbEgress,
		})
		if err != nil {
			return fmt.Errorf("cgroup egress: %w", err)
		}
		c.closers = append(c.closers, l.Close)
		c.logger.Info("cgroup_skb/egress attached", "path", cgPath)
	}

	return nil
}
