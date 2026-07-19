-- ═══════════════════════════════════════════════════════════════════
-- Инициализация схемы NTA: целевые таблицы + Kafka Engine + MV
-- Выполняется автоматически при первом старте контейнера ClickHouse.
-- База traffic и пользователь traffic создаются переменными окружения.
-- ═══════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────
-- 1. ЦЕЛЕВЫЕ ТАБЛИЦЫ (MergeTree, с TTL)
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS traffic.host_profiles
(
    host_id           String,
    window_start      DateTime64(3),
    window_end        DateTime64(3),
    window_type       Enum8('tumbling' = 1, 'sliding' = 2, 'session' = 3),
    packets           UInt64,
    bytes             UInt64,
    pps               Float64,
    bps               Float64,
    uniq_dst_ip       UInt32,
    uniq_dst_port     UInt32,
    proto_tcp         UInt64,
    proto_udp         UInt64,
    proto_other       UInt64,
    conn_interval_avg Float64,
    conn_interval_std Float64,
    version           UInt64
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMMDD(window_start)
ORDER BY (host_id, window_type, window_start)
TTL toDateTime(window_start) + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS traffic.alerts
(
    alert_id      String,
    host_id       String,
    detected_at   DateTime64(3),
    window_start  DateTime64(3),
    detector      LowCardinality(String),
    category      LowCardinality(String),
    severity      Enum8('low' = 1, 'medium' = 2, 'high' = 3, 'critical' = 4),
    risk_score    Float64,
    model_version LowCardinality(String) DEFAULT '',
    details       String,
    version       UInt64
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMMDD(detected_at)
ORDER BY (host_id, detected_at, detector)
TTL toDateTime(detected_at) + INTERVAL 90 DAY;

-- ───────────────────────────────────────────────────────────────────
-- 2. KAFKA ENGINE (очереди чтения из топиков, формат JSONEachRow)
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS traffic.profiles_queue
(
    host_id           String,
    window_start      DateTime64(3),
    window_end        DateTime64(3),
    window_type       String,
    packets           UInt64,
    bytes             UInt64,
    pps               Float64,
    bps               Float64,
    uniq_dst_ip       UInt32,
    uniq_dst_port     UInt32,
    proto_tcp         UInt64,
    proto_udp         UInt64,
    proto_other       UInt64,
    conn_interval_avg Float64,
    conn_interval_std Float64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list      = 'kafka:9094',
    kafka_topic_list       = 'traffic.profiles',
    kafka_group_name       = 'ch-profiles-writer',
    kafka_format           = 'JSONEachRow',
    kafka_num_consumers    = 1,
    kafka_skip_broken_messages = 100;

CREATE TABLE IF NOT EXISTS traffic.alerts_queue
(
    alert_id      String,
    host_id       String,
    detected_at   DateTime64(3),
    window_start  DateTime64(3),
    detector      String,
    category      String,
    severity      UInt8,
    risk_score    Float64,
    model_version String,
    details       String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list      = 'kafka:9094',
    kafka_topic_list       = 'traffic.alerts',
    kafka_group_name       = 'ch-alerts-writer',
    kafka_format           = 'JSONEachRow',
    kafka_num_consumers    = 1,
    kafka_skip_broken_messages = 100;

-- ───────────────────────────────────────────────────────────────────
-- 3. MATERIALIZED VIEW (перекладывают из очереди в целевые таблицы)
--    version = момент вставки в мс → корректная дедупликация ReplacingMergeTree
-- ───────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS traffic.profiles_mv
TO traffic.host_profiles AS
SELECT
    host_id,
    window_start,
    window_end,
    window_type,                    -- строка приводится к Enum8 целевой таблицы
    packets,
    bytes,
    pps,
    bps,
    uniq_dst_ip,
    uniq_dst_port,
    proto_tcp,
    proto_udp,
    proto_other,
    conn_interval_avg,
    conn_interval_std,
    toUnixTimestamp64Milli(now64(3)) AS version
FROM traffic.profiles_queue;

CREATE MATERIALIZED VIEW IF NOT EXISTS traffic.alerts_mv
TO traffic.alerts AS
SELECT
    alert_id,
    host_id,
    detected_at,
    window_start,
    detector,
    category,
    severity,                       -- UInt8 (1..4) приводится к Enum8
    risk_score,
    model_version,
    details,
    toUnixTimestamp64Milli(now64(3)) AS version
FROM traffic.alerts_queue;
