package store

import (
	"context"
	"fmt"

	"github.com/ClickHouse/clickhouse-go/v2"
)

const migrateHosts = `
CREATE TABLE IF NOT EXISTS hosts (
    host_id        String,
    hostname       String,
    os             String,
    arch           String,
    kernel_version String,
    interfaces     Array(String),
    boot_time      DateTime,
    registered_at  DateTime,
    updated_at     DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (host_id)
`

const migratePackets = `
CREATE TABLE IF NOT EXISTS packets (
    timestamp    DateTime64(9, 'UTC'),
    host_id      LowCardinality(String),
    src_ip       IPv4,
    dst_ip       IPv4,
    src_port     UInt16,
    dst_port     UInt16,
    pkt_len      UInt32,
    protocol     UInt8,
    hook_type    UInt8,
    direction    UInt8,
    if_index     UInt32,
    received_at  DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (host_id, timestamp, src_ip, dst_ip)
TTL toDateTime(timestamp) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192
`

func Migrate(ctx context.Context, conn clickhouse.Conn) error {
	if err := conn.Exec(ctx, migrateHosts); err != nil {
		return fmt.Errorf("migrate hosts: %w", err)
	}
	if err := conn.Exec(ctx, migratePackets); err != nil {
		return fmt.Errorf("migrate packets: %w", err)
	}
	return nil
}
