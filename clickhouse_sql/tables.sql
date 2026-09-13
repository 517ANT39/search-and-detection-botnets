-- 1. Базовая
CREATE TABLE IF NOT EXISTS traffic_stats (
    window_start   DateTime,
    src_ip         String,
    dst_ip         String,
    src_port       UInt16,
    dst_port       UInt16,
    protocol       UInt8,
    direction      UInt8,
    packet_count   UInt64,
    byte_sum       UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (src_ip, dst_ip, src_port, dst_port, protocol, direction, window_start)
TTL window_start + INTERVAL 30 DAY;

-- 2. Rollup'ы
CREATE TABLE IF NOT EXISTS traffic_stats_by_protocol (
    window_start DateTime, protocol UInt8,
    packet_count UInt64, byte_sum UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (protocol, window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS traffic_stats_by_port (
    window_start DateTime, port UInt16, port_type String,
    packet_count UInt64, byte_sum UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (port_type, port, window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS traffic_stats_by_direction (
    window_start DateTime, direction UInt8,
    packet_count UInt64, byte_sum UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (direction, window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS traffic_stats_by_host (
    window_start DateTime, host_ip String, role String,
    packet_count UInt64, byte_sum UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (host_ip, role, window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS traffic_stats_by_subnet (
    window_start DateTime, src_subnet String, dst_subnet String,
    packet_count UInt64, byte_sum UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (src_subnet, dst_subnet, window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS traffic_stats_by_pair (
    window_start DateTime, src_ip String, dst_ip String, protocol UInt8,
    packet_count UInt64, byte_sum UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (src_ip, dst_ip, protocol, window_start)
TTL window_start + INTERVAL 7 DAY;

-- 3. Top-N
CREATE TABLE IF NOT EXISTS traffic_top_sources (
    window_start DateTime, src_ip String,
    packet_count UInt64, byte_sum UInt64, rank UInt8
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (window_start, rank)
TTL window_start + INTERVAL 7 DAY;

CREATE TABLE IF NOT EXISTS traffic_top_targets (
    window_start DateTime, dst_ip String,
    packet_count UInt64, byte_sum UInt64, rank UInt8
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (window_start, rank)
TTL window_start + INTERVAL 7 DAY;

-- 4. Хосты
CREATE TABLE IF NOT EXISTS hosts_info (
    host_id         String,
    hostname        String,
    os              String,
    arch            String,
    kernel_version  String,
    interfaces      String,
    boot_time_sec   DateTime,
    register_ts     DateTime
) ENGINE = ReplacingMergeTree(register_ts)
ORDER BY host_id;

CREATE TABLE IF NOT EXISTS alerts (
    timestamp        DateTime,
    detector         String,          -- "peer" | "rolling"
    view             String,          -- "flow" | "src_dst" | "dst_service" | "src" | "dst" | "protocol"
    src_ip           String,
    src_port         Int32,           -- -1 если не применимо
    dst_ip           String,
    dst_port         Int32,           -- -1 если не применимо
    protocol         Int32,           -- -1 если не применимо
    direction        Int32,           -- -1 = unknown
    packet_count     UInt64,
    byte_sum         UInt64,
    active_minutes   Int32,
    avg_per_min      Float64,
    baseline_value   Float64,
    baseline_stddev  Float64,
    z_score          Float64,
    anomaly_type     String,
    severity         String,          -- "info" | "warning" | "critical"
    host_id          String DEFAULT ''
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, detector, view, dst_ip)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

ALTER TABLE alerts ADD INDEX IF NOT EXISTS idx_src_ip src_ip TYPE bloom_filter GRANULARITY 4;
ALTER TABLE alerts ADD INDEX IF NOT EXISTS idx_dst_ip dst_ip TYPE bloom_filter GRANULARITY 4;
ALTER TABLE alerts ADD INDEX IF NOT EXISTS idx_severity severity TYPE set(4) GRANULARITY 4;
ALTER TABLE alerts ADD INDEX IF NOT EXISTS idx_view view TYPE set(10) GRANULARITY 4;
