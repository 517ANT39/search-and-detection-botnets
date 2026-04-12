module monitoring-agent

go 1.24.0

require (
	github.com/cilium/ebpf v0.21.0
	github.com/google/uuid v1.6.0
	github.com/vishvananda/netlink v1.3.0
	golang.org/x/sys v0.37.0
	google.golang.org/grpc v1.70.0
	google.golang.org/protobuf v1.35.2
	gopkg.in/yaml.v3 v3.0.1
)

require (
	github.com/vishvananda/netns v0.0.4 // indirect
	golang.org/x/net v0.46.0 // indirect
	golang.org/x/text v0.30.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20241202173237-19429a94021a // indirect
)

tool github.com/cilium/ebpf/cmd/bpf2go
