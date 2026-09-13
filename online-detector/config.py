import os

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
PACKETS_TOPIC   = os.getenv("PACKETS_TOPIC", "traffic.packets")
ALERT_TOPIC     = os.getenv("ALERT_TOPIC", "traffics.alert")
SPARK_CLUSTER = os.getenv("SPARK_CLUSTER","local[*]")

# ClickHouse
CLICKHOUSE_HOST     = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT     = os.getenv("CLICKHOUSE_PORT", "8123")
CLICKHOUSE_DB       = os.getenv("CLICKHOUSE_DB", "netsentry")
CLICKHOUSE_USER     = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "pass")
CLICKHOUSE_JDBC_URL = f"jdbc:clickhouse://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DB}"

JDBC_PROPS = {
    "driver":   "com.clickhouse.jdbc.ClickHouseDriver",
    "user":     CLICKHOUSE_USER,
    "password": CLICKHOUSE_PASSWORD,
}


WINDOW_DURATION  = "5 minutes"
SLIDE_DURATION   = "1 minute"
WATERMARK_DELAY  = "2 minutes"
TRIGGER_INTERVAL = "1 minute"

# Пороги peer-детектора
PEER_MIN_KEYS = 10    # минимум ключей в окне для статистики
PEER_TOP_K    = 50    # сколько аномалий максимум отдавать на окно

# Срезы: (имя, ключи группировки, z-порог)
PEER_VIEWS = [
    ("flow",        ["src_ip", "src_port", "dst_ip", "dst_port", "protocol"], 3.5),
    ("src_dst",     ["src_ip", "dst_ip"],                                      4.0),
    ("dst_service", ["dst_ip", "dst_port", "protocol"],                        3.0),
    ("src",         ["src_ip"],                                                4.5),
    ("dst",         ["dst_ip"],                                                4.5),
    ("protocol",    ["protocol"],                                              3.0),
]

SEV_WARNING  = 3.0
SEV_CRITICAL = 5.0