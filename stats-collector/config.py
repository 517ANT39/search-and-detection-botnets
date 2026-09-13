import os

SPARK_CLUSTER = os.getenv("SPARK_CLUSTER","local[*]")

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TRAFFIC_TOPIC   = os.getenv("TRAFFIC_TOPIC", "traffic.packets")
HOST_TOPIC      = os.getenv("HOST_TOPIC", "traffic.hosts")

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

# Окна
WINDOW_DURATION = "1 minute"
SLIDE_DURATION  = "1 minute"
WATERMARK_DELAY = "1 minute"

# Top-N
TOP_N = 10