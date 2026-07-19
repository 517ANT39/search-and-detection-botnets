package utils

import (
	pb "monitoring-agent/gen/traffic"
)

func DecodeProtocol(protocolNum uint8) pb.Protocol {

	switch protocolNum {
	case 6:
		return pb.Protocol_IPPROTO_TCP
	case 17:
		return pb.Protocol_IPPROTO_UDP
	case 1:
		return pb.Protocol_IPPROTO_ICMP
	default:
		return pb.Protocol_UNKNOWN
	}

}
