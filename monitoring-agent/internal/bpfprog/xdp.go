package bpfprog

import (
	"fmt"
	"net"

	"github.com/cilium/ebpf/link"
)

func (c *Collector) attachXDP() error {
	for _, ifName := range c.cfg.Capture.Interfaces {
		if err := c.xdpAttach(ifName); err != nil {
			return fmt.Errorf("xdp %s: %w", ifName, err)
		}
	}
	return nil
}

func (c *Collector) xdpAttach(ifName string) error {
	iface, err := net.InterfaceByName(ifName)
	if err != nil {
		return err
	}

	l, err := link.AttachXDP(link.XDPOptions{
		Program:   c.objs.XdpTraffic,
		Interface: iface.Index,
		Flags:     link.XDPAttachFlags(c.cfg.Capture.XDPFlags),
	})
	if err != nil {
		return fmt.Errorf("attach xdp: %w", err)
	}

	c.logger.Info("XDP attached", "iface", ifName)
	c.closers = append(c.closers, l.Close)
	return nil
}
