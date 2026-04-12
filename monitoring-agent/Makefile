CLANG       ?= clang
BPFTOOL     ?= bpftool
GO          ?= go
PROTOC      ?= protoc

BPF_HDR_DIR := bpf
GEN_DIR     := internal/bpfprog
PROTO_DIR   := ../proto
PROTO_OUT   := gen/traffic
BIN_DIR     := bin

AGENT_BIN   := $(BIN_DIR)/monitoring-agent

.PHONY: all clean submodule generate proto build vmlinux fmt

all: submodule generate proto build

# ── Git submodule ──────────────────────────────────────────
submodule:
	@echo ">>> Updating git submodules…"
	git submodule update --init --recursive

# ── bpf2go: C → Go bindings ───────────────────────────────
generate: submodule
	@echo ">>> Generating eBPF Go bindings…"
	cd $(GEN_DIR) && $(GO) generate ./...

# ── protobuf / gRPC stubs ─────────────────────────────────
proto:
	@echo ">>> Generating protobuf…"
	@mkdir -p $(PROTO_OUT)
	$(PROTOC) \
		--proto_path=$(PROTO_DIR) \
		--go_out=./gen/traffic --go_opt=paths=source_relative \
		--go-grpc_out=./gen/traffic --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/traffic.proto

# ── agent binary ───────────────────────────────────────────
build:
	@echo ">>> Building agent…"
	@mkdir -p $(BIN_DIR)
	CGO_ENABLED=0 $(GO) build -trimpath -ldflags="-s -w" \
		-o $(AGENT_BIN) ./cmd/agent

# ── helpers ────────────────────────────────────────────────
vmlinux:
	$(BPFTOOL) btf dump file /sys/kernel/btf/vmlinux format c > $(BPF_HDR_DIR)/vmlinux.h

fmt:
	$(GO) fmt ./...

clean:
	rm -rf $(BIN_DIR)
	rm -f $(GEN_DIR)/traffic_bpf*.go $(GEN_DIR)/traffic_bpf*.o
	rm -f $(PROTO_OUT)/*.go
