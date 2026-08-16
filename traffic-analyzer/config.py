import os

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
INPUT_TOPIC = "traffic.packets"
ALERT_TOPIC = "alerts"

# ClickHouse
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "jdbc:clickhouse://localhost:8123/netsentry")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "pass")
CLICKHOUSE_TABLE = "traffic_stats"
HOST_TOPIC = os.getenv("HOST_TOPIC", "traffic.hosts")   

# Окна и временные параметры
WINDOW_DURATION = "1 minute"
SLIDE_DURATION = "1 minute"
WATERMARK_DELAY = "1 minute"          # Задержка для опоздавших данных
HISTORY_INTERVAL = 30                  # Минут для скользящей истории (обучение)
MIN_HISTORY_WINDOWS = 10               # Минимальное число окон для начала детекции
REFRESH_MODEL_INTERVAL = 5             # Минут – периодичность переобучения (в реальном проекте можно вынести)

# Параметры моделей
ISOLATION_FOREST_CONFIG = {
    "n_estimators": 100,
    "contamination": 0.01,             # ожидаемая доля аномалий
    "random_state": 42,
    "n_jobs": -1,
}
LOF_CONFIG = {
    "n_neighbors": 20,
    "contamination": 0.01,
    "metric": "euclidean",
    "algorithm": "auto",
}
ANOMALY_THRESHOLD = 0.5                # Если средняя оценка аномалий > порога (0..1) – алерт

# Пути для сохранения моделей (если нужно сохранять на диск)
MODEL_DIR = "/tmp/models"