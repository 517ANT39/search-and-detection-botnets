package bpfprog

import (
	"fmt"
	"net"

	"github.com/vishvananda/netlink"
	"golang.org/x/sys/unix"
)

// attachTCBoth attaches both ingress and egress TC classifiers.
func (c *Collector) attachTCBoth() error {
	for _, ifName := range c.cfg.Capture.Interfaces {
		if err := c.tcAttach(ifName, true, true); err != nil {
			return err
		}
	}
	return nil
}

// attachTCEgress attaches only TC egress classifier.
func (c *Collector) attachTCEgress() error {
	for _, ifName := range c.cfg.Capture.Interfaces {
		if err := c.tcAttach(ifName, false, true); err != nil {
			return err
		}
	}
	return nil
}

func (c *Collector) tcAttach(ifName string, ingress, egress bool) error {
	iface, err := net.InterfaceByName(ifName)
	if err != nil {
		return fmt.Errorf("interface %s: %w", ifName, err)
	}
	link, err := netlink.LinkByIndex(iface.Index)
	if err != nil {
		return err
	}

	idx := link.Attrs().Index

	// ensure clsact qdisc
	qdisc := &netlink.GenericQdisc{
		QdiscAttrs: netlink.QdiscAttrs{
			LinkIndex: idx,
			Handle:    netlink.MakeHandle(0xffff, 0),
			Parent:    netlink.HANDLE_CLSACT,
		},
		QdiscType: "clsact",
	}
	_ = netlink.QdiscAdd(qdisc)

	if ingress {
		f := &netlink.BpfFilter{
			FilterAttrs: netlink.FilterAttrs{
				LinkIndex: idx,
				Parent:    netlink.HANDLE_MIN_INGRESS,
				Handle:    1,
				Protocol:  unix.ETH_P_ALL,
				Priority:  1,
			},
			Fd:           c.objs.TcClsIngress.FD(),
			Name:         "tc_cls_ingress",
			DirectAction: true,
		}
		if err := netlink.FilterAdd(f); err != nil {
			return fmt.Errorf("tc ingress %s: %w", ifName, err)
		}
		c.logger.Info("TC ingress attached", "iface", ifName)
	}

	if egress {
		f := &netlink.BpfFilter{
			FilterAttrs: netlink.FilterAttrs{
				LinkIndex: idx,
				Parent:    netlink.HANDLE_MIN_EGRESS,
				Handle:    1,
				Protocol:  unix.ETH_P_ALL,
				Priority:  1,
			},
			Fd:           c.objs.TcClsEgress.FD(),
			Name:         "tc_cls_egress",
			DirectAction: true,
		}
		if err := netlink.FilterAdd(f); err != nil {
			return fmt.Errorf("tc egress %s: %w", ifName, err)
		}
		c.logger.Info("TC egress attached", "iface", ifName)
	}

	// cleanup: remove whole clsact qdisc (removes all filters)
	c.closers = append(c.closers, func() error {
		lnk, err := netlink.LinkByIndex(idx)
		if err != nil {
			return err
		}
		q := &netlink.GenericQdisc{
			QdiscAttrs: netlink.QdiscAttrs{
				LinkIndex: lnk.Attrs().Index,
				Handle:    netlink.MakeHandle(0xffff, 0),
				Parent:    netlink.HANDLE_CLSACT,
			},
			QdiscType: "clsact",
		}
		return netlink.QdiscDel(q)
	})

	return nil
}
