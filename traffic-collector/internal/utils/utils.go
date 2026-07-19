package utils

import (
	"encoding/binary"
	"net"
	pb "traffic-collector/gen/traffic"
)

func ToPacketInfo(packet *pb.PacketEvent) *pb.PacketInfo {

	return &pb.PacketInfo{
		TimestampNs: packet.TimestampNs,
		SrcIp:       parseIp(packet.SrcIp).String(),
		DstIp:       parseIp(packet.DstIp).String(),
		DstPort:     packet.DstPort,
		SrcPort:     packet.SrcPort,
		PktLen:      packet.PktLen,
		Hook:        packet.Hook,
		Direction:   packet.Direction,
		Ifindex:     packet.Ifindex,
	}

}

func parseIp(rawIP uint32) net.IP {

	ip := make(net.IP, 4)
	binary.BigEndian.PutUint32(ip, rawIP)

	return ip

}
