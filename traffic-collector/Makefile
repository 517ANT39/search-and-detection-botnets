GO      ?= go
PROTOC  ?= protoc

PROTO_DIR   := ../proto
PROTO_OUT   := gen/traffic
BIN_DIR     := bin

.PHONY: all proto build clean

all: proto build

# ── protobuf / gRPC stubs ─────────────────────────────────
proto:
	@echo ">>> Generating protobuf…"
	@mkdir -p $(PROTO_OUT)
	$(PROTOC) \
		--proto_path=$(PROTO_DIR) \
		--go_out=./gen/traffic --go_opt=paths=source_relative \
		--go-grpc_out=./gen/traffic --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/traffic.proto

build:
	@echo ">>> Building collector…"
	@mkdir -p $(BIN_DIR)
	CGO_ENABLED=0 $(GO) build -trimpath -ldflags="-s -w" \
		-o $(BIN_DIR)/traffic-collector ./cmd/collector

clean:
	rm -rf $(BIN_DIR) gen/traffic/*.go
