from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, lit, when, current_timestamp, count as _count,
    sum as _sum, avg, stddev, row_number, broadcast,
)
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, TimestampType, StringType,
    IntegerType, LongType, DoubleType,
)

from config import (
    PEER_MIN_KEYS, PEER_TOP_K, PEER_VIEWS,
    SEV_WARNING, SEV_CRITICAL,
)


ALERT_SCHEMA = StructType([
    StructField("timestamp",       TimestampType(), True),
    StructField("detector",        StringType(),    True),
    StructField("view",            StringType(),    True),
    StructField("src_ip",          StringType(),    True),
    StructField("src_port",        IntegerType(),   True),
    StructField("dst_ip",          StringType(),    True),
    StructField("dst_port",        IntegerType(),   True),
    StructField("protocol",        IntegerType(),   True),
    StructField("direction",       IntegerType(),   True),
    StructField("packet_count",    LongType(),      True),
    StructField("byte_sum",        LongType(),      True),
    StructField("active_minutes",  IntegerType(),   True),
    StructField("avg_per_min",     DoubleType(),    True),
    StructField("baseline_value",  DoubleType(),    True),
    StructField("baseline_stddev", DoubleType(),    True),
    StructField("z_score",         DoubleType(),    True),
    StructField("anomaly_type",    StringType(),    True),
    StructField("severity",        StringType(),    True),
    StructField("host_id",         StringType(),    True),
])


def _detect_view(df_window: DataFrame, spark: SparkSession,
                 view_name: str, group_keys: list, z_threshold: float) -> DataFrame:
    """
    Все вычисления — только внутри окна. Никакой истории.
    df_window: строки вида (window_start, 5-tuple, packet_count, byte_sum).
    """
    # 1. Свернуть до нужного среза внутри окна
    agg = (
        df_window
        .groupBy("window_start", *group_keys)
        .agg(
            _sum("packet_count").alias("packet_count"),
            _sum("byte_sum").alias("byte_sum"),
            _count("*").alias("buckets"),
        )
    )

    # 2. Статистика по всем ключам ЭТОГО ЖЕ окна
    peer_stats = (
        agg
        .groupBy("window_start")
        .agg(
            avg("packet_count").alias("peer_avg"),
            stddev("packet_count").alias("peer_std"),
            _count("*").alias("keys_count"),
        )
        .filter(col("keys_count") >= PEER_MIN_KEYS)
    )

    # 3. Z-score
    joined = (
        agg
        .join(broadcast(peer_stats), on="window_start", how="inner")
        .withColumn(
            "z_packets",
            when(col("peer_std") > 0,
                 (col("packet_count") - col("peer_avg")) / col("peer_std"))
            .otherwise(lit(0.0)),
        )
        .withColumn("avg_per_min", col("packet_count") / col("buckets"))
    )

    # 4. Top-K аномалий в окне
    w = Window.partitionBy("window_start").orderBy(col("z_packets").desc())

    anomalies = (
        joined
        .filter(col("z_packets") > z_threshold)
        .withColumn("rank", row_number().over(w))
        .filter(col("rank") <= PEER_TOP_K)
        .withColumn("timestamp", current_timestamp())
        .withColumn("detector", lit("peer"))
        .withColumn("view", lit(view_name))
        .withColumn("direction", lit(-1).cast("int"))
        .withColumn("host_id", lit(""))
        .withColumn(
            "severity",
            when(col("z_packets") > SEV_CRITICAL, lit("critical"))
            .when(col("z_packets") > SEV_WARNING, lit("warning"))
            .otherwise(lit("info")),
        )
        .withColumn("anomaly_type", lit("peer_outlier"))
        .withColumn("baseline_value", col("peer_avg"))
        .withColumn("baseline_stddev", col("peer_std"))
        .withColumn("z_score", col("z_packets"))
        .withColumn("active_minutes", col("buckets").cast("int"))
    )

    # 5. Заполнить отсутствующие ключи
    for k, default in [
        ("src_ip", ""), ("src_port", -1),
        ("dst_ip", ""), ("dst_port", -1),
        ("protocol", -1),
    ]:
        if k not in group_keys:
            anomalies = anomalies.withColumn(
                k, lit(default).cast("int" if isinstance(default, int) else "string")
            )

    return anomalies.select(
        "timestamp", "detector", "view",
        "src_ip", "src_port", "dst_ip", "dst_port", "protocol",
        "direction",
        "packet_count", "byte_sum",
        "active_minutes", "avg_per_min",
        "baseline_value", "baseline_stddev",
        "z_score", "anomaly_type", "severity",
        "host_id",
    )


def detect_all_views(df_window: DataFrame, spark: SparkSession) -> DataFrame:
    """Прогоняет все срезы и объединяет результаты."""
    results = []
    for view_name, keys, z_th in PEER_VIEWS:
        try:
            r = _detect_view(df_window, spark, view_name, keys, z_th)
            results.append(r)
        except Exception as e:
            print(f"[detector/{view_name}] ошибка: {e}")

    if not results:
        return spark.createDataFrame([], ALERT_SCHEMA)

    out = results[0]
    for r in results[1:]:
        out = out.unionByName(r)
    return out