-- Основная таблица агрегированного трафика (по 5‑tuple + direction)
CREATE TABLE IF NOT EXISTS traffic_stats (
    window_start   DateTime,          -- начало минутного окна
    src_ip         String,
    dst_ip         String,
    src_port       UInt16,
    dst_port       UInt16,
    protocol       UInt8,             -- 0=TCP, 1=UDP, 2=ICMP, 3=UNKNOWN
    direction      UInt8,             -- 0=INGRESS, 1=EGRESS
    packet_count   UInt64,
    byte_sum       UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (src_ip, dst_ip, src_port, dst_port, protocol, direction, window_start)
SETTINGS index_granularity = 8192;

-- Таблица для хостов (информация о агентах)
CREATE TABLE IF NOT EXISTS hosts_info (
    host_id         String,
    hostname        String,
    os              String,
    arch            String,
    kernel_version  String,
    interfaces      String,           -- JSON-строка {ifindex: name}
    boot_time_sec   DateTime,         -- время загрузки (можно хранить как DateTime)
    register_ts     DateTime          -- время регистрации
) ENGINE = ReplacingMergeTree(register_ts)
ORDER BY host_id;

-- Таблица для алертов
CREATE TABLE IF NOT EXISTS alerts (
    timestamp        DateTime,        -- время возникновения аномалии
    src_ip           String,
    dst_ip           String,
    src_port         UInt16,
    dst_port         UInt16,
    protocol         UInt8,
    direction        UInt8,
    packet_count     UInt64,
    byte_sum         UInt64,
    threshold_count  Float64,
    threshold_bytes  Float64,
    anomaly_type     String,
    host_id          String
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, src_ip, dst_ip)
SETTINGS index_granularity = 8192;

-- Статистика по хостам (агрегировано по host_ip)
CREATE TABLE IF NOT EXISTS traffic_stats_by_host (
    window_start   DateTime,
    host_ip        String,
    direction      UInt8,             -- 0 – исходящий (src), 1 – входящий (dst)
    packet_count   UInt64,
    byte_sum       UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (host_ip, direction, window_start);

-- Статистика по протоколам
CREATE TABLE IF NOT EXISTS traffic_stats_by_protocol (
    window_start   DateTime,
    protocol       UInt8,
    packet_count   UInt64,
    byte_sum       UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (protocol, window_start);

-- Статистика по портам (только для TCP/UDP)
CREATE TABLE IF NOT EXISTS traffic_stats_by_port (
    window_start   DateTime,
    port           UInt16,
    packet_count   UInt64,
    byte_sum       UInt64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (port, window_start);