# streaming_processor.py
import os
import json
import pickle
import signal
import sys
import threading
import time
from datetime import datetime
import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, window, count, sum as _sum, udf, struct, to_json, concat, lit
)
from pyspark.sql.types import DoubleType, StructType, StructField, StringType, LongType, IntegerType
from pyspark.sql.streaming import StreamingQuery

from clickhouse_utils import (
    write_stats_to_clickhouse,
    write_hosts_to_clickhouse,
    write_additional_stats,
    read_recent_stats,
)
from config import *
from feature_extraction import add_features, FEATURE_COLUMNS
from model_manager import AnomalyEnsemble
from protobuf_utils import decode_packet, PACKET_SCHEMA
import models.traffic_send_analyze_pb2 as traffic_pb2
import models.host_info_pb2 as host_info_pb2

decode_udf = udf(decode_packet, PACKET_SCHEMA)
# -------------------- HostInfo UDF --------------------
HOST_SCHEMA = StructType([
    StructField("host_id", StringType(), True),
    StructField("hostname", StringType(), True),
    StructField("os", StringType(), True),
    StructField("arch", StringType(), True),
    StructField("kernel_version", StringType(), True),
    StructField("interfaces", StringType(), True),  # JSON-строка
    StructField("boot_time_sec", LongType(), True),
    StructField("register_ts", LongType(), True),
])

def decode_host(pb_bytes: bytes) -> dict:
    """Декодирует Protobuf HostInfo в словарь, интерфейсы преобразует в JSON."""
    h = host_info_pb2.HostInfo()
    h.ParseFromString(pb_bytes)
    interfaces_json = json.dumps({k: v for k, v in h.interfaces.items()})
    return {
        "host_id": h.host_id,
        "hostname": h.hostname,
        "os": h.os,
        "arch": h.arch,
        "kernel_version": h.kernel_version,
        "interfaces": interfaces_json,
        "boot_time_sec": h.boot_time_sec,
        "register_ts": h.register_ts,
    }

decode_host_udf = udf(decode_host, HOST_SCHEMA)

# -------------------- Модель и предсказание --------------------
# Глобальная директория для модели
MODEL_DIR = os.getenv("MODEL_DIR", "/tmp/models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_and_save_model(spark: SparkSession, atomic: bool = True) -> bool:
    """Обучает модель на исторических данных и сохраняет атомарно."""
    df_hist = read_recent_stats(spark, HISTORY_INTERVAL)
    if df_hist.count() < MIN_HISTORY_WINDOWS:
        print(f"[{datetime.now()}] Недостаточно данных для обучения: {df_hist.count()} окон.")
        return False

    df_feat = add_features(df_hist)
    X = df_feat.select(FEATURE_COLUMNS).toPandas().values
    if X.shape[0] < MIN_HISTORY_WINDOWS:
        return False

    ensemble = AnomalyEnsemble()
    ensemble.fit(X)

    model_path = os.path.join(MODEL_DIR, "ensemble.pkl")
    temp_path = model_path + ".tmp"

    with open(temp_path, "wb") as f:
        pickle.dump(ensemble, f)

    if atomic:
        os.replace(temp_path, model_path)
    else:
        os.rename(temp_path, model_path)

    print(f"[{datetime.now()}] Модель обновлена (обучено на {X.shape[0]} точках).")
    return True

def periodic_training(spark: SparkSession):
    """Фоновый поток переобучения."""
    while True:
        time.sleep(REFRESH_MODEL_INTERVAL * 60)
        try:
            train_and_save_model(spark, atomic=True)
        except Exception as e:
            print(f"[{datetime.now()}] Ошибка переобучения: {e}")

def predict_anomaly_udf(packet_count, byte_sum, avg_packet_size, log_packet_count, log_byte_sum):
    """UDF, загружающая модель из файла с кешированием по времени модификации."""
    import pickle
    import os
    import numpy as np
    _model_cache = None
    _model_mtime = None

    def _get_model():
        nonlocal _model_cache, _model_mtime
        model_path = os.path.join(MODEL_DIR, "ensemble.pkl")
        current_mtime = os.path.getmtime(model_path) if os.path.exists(model_path) else None
        if _model_cache is None or _model_mtime != current_mtime:
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    _model_cache = pickle.load(f)
                    _model_mtime = current_mtime
            else:
                _model_cache = None
        return _model_cache

    model = _get_model()
    if model is None:
        return 0.5
    X = np.array([packet_count, byte_sum, avg_packet_size, log_packet_count, log_byte_sum]).reshape(1, -1)
    score = model.predict_proba(X)[0]
    return float(score)

predict_udf = udf(predict_anomaly_udf, DoubleType())

# -------------------- Обработка батчей --------------------
def process_batch(df: DataFrame, epoch_id: int):
    """Обработка основного батча: запись статистик и детекция аномалий."""
    if df.count() == 0:
        return

    # 1. Запись агрегатов в основную таблицу
    write_stats_to_clickhouse(df, epoch_id)

    # 2. Запись дополнительных статистик (по хостам, протоколам, портам)
    write_additional_stats(df, epoch_id)

    # 3. Детекция аномалий
    df_feat = add_features(df)
    scores_df = df_feat.select(
        col("window_start"),
        col("src_ip"),
        col("dst_ip"),
        col("src_port"),
        col("dst_port"),
        col("protocol"),
        col("direction"),
        col("packet_count"),
        col("byte_sum"),
        predict_udf(
            col("packet_count"),
            col("byte_sum"),
            col("avg_packet_size"),
            col("log_packet_count"),
            col("log_byte_sum")
        ).alias("anomaly_score")
    )

    alerts = scores_df.filter(col("anomaly_score") > ANOMALY_THRESHOLD)
    if alerts.count() > 0:
        # Переименуем window_start в timestamp для бэкенда
        alerts = alerts.withColumnRenamed("window_start", "timestamp")
        alerts_kafka = alerts.select(
            concat(col("src_ip"), lit("-"), col("dst_ip")).alias("key"),
            to_json(struct("*")).alias("value")
        )
        alerts_kafka.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
            .option("topic", ALERT_TOPIC) \
            .mode("append") \
            .save()

# -------------------- Главный запуск --------------------
def start_streaming():
    spark = SparkSession.builder \
        .appName("TrafficAnomalyEnsemble") \
        .master("local[*]") \
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0,com.clickhouse:clickhouse-jdbc:0.10.0") \
        .config("spark.sql.shuffle.partitions", 200) \
        .config("spark.sql.streaming.statefulOperator.checkCorrectness.enabled", "false") \
        .getOrCreate()

    # Подготовка модели
    train_and_save_model(spark, atomic=True)
    threading.Thread(target=periodic_training, args=(spark,), daemon=True).start()

    # ----- Поток трафика (основной) -----
    raw_traffic = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    packets = raw_traffic \
        .select(decode_udf(col("value")).alias("packet")) \
        .select("packet.*") \
        .withColumn("timestamp", (col("timestamp_ns") / 1e9).cast("timestamp"))

    traffic_agg = packets \
        .withWatermark("timestamp", WATERMARK_DELAY) \
        .groupBy(
            window("timestamp", WINDOW_DURATION, SLIDE_DURATION),
            col("src_ip"), col("dst_ip"), col("src_port"),
            col("dst_port"), col("protocol"), col("direction")
        ) \
        .agg(
            count("*").alias("packet_count"),
            _sum("pkt_len").alias("byte_sum")
        ) \
        .withColumn("window_start", col("window.start").cast("timestamp"))

    traffic_query = traffic_agg.writeStream \
        .foreachBatch(process_batch) \
        .outputMode("append") \
        .trigger(processingTime="1 minute") \
        .option("checkpointLocation", "/tmp/checkpoints/traffic_ensemble") \
        .start()

    # ----- Поток хостов (HostInfo) -----
    raw_hosts = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", HOST_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    hosts = raw_hosts \
        .select(decode_host_udf(col("value")).alias("host")) \
        .select("host.*")

    host_query = hosts.writeStream \
        .foreachBatch(write_hosts_to_clickhouse) \
        .outputMode("append") \
        .trigger(processingTime="10 seconds") \
        .option("checkpointLocation", "/tmp/checkpoints/hosts") \
        .start()

    # ---- Обработка сигналов остановки ----
    def shutdown_handler(signum, frame):
        print(f"\n[{datetime.now()}] Получен сигнал {signum}, останавливаем стримы...")
        traffic_query.stop()
        host_query.stop()
        spark.stop()
        print("Остановка завершена.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Ожидание завершения
    try:
        spark.streams.awaitAnyTermination()
    except KeyboardInterrupt:
        shutdown_handler(signal.SIGINT, None)

if __name__ == "__main__":
    start_streaming()