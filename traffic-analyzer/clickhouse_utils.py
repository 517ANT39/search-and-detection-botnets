# clickhouse_utils.py
from pyspark.sql import DataFrame
from config import CLICKHOUSE_URL, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD
from pyspark.sql.functions import col, lit, sum as _sum

JDBC_PROPS = {
    "driver": "com.clickhouse.jdbc.ClickHouseDriver",
    "user": CLICKHOUSE_USER,
    "password": CLICKHOUSE_PASSWORD,
}

def write_stats_to_clickhouse(df: DataFrame, epoch_id: int):
    if df.count() == 0:
        return
    df.select("window_start", "src_ip", "dst_ip", "src_port", "dst_port",
              "protocol", "direction", "packet_count", "byte_sum") \
      .write.jdbc(url=CLICKHOUSE_URL, table="traffic_stats", mode="append", properties=JDBC_PROPS)

def write_hosts_to_clickhouse(df: DataFrame, epoch_id: int):
    if df.count() == 0:
        return
    # Используем режим append, но для избежания дублей можно использовать ReplacingMergeTree
    df.write.jdbc(url=CLICKHOUSE_URL, table="hosts_info", mode="append", properties=JDBC_PROPS)

def write_additional_stats(df: DataFrame, epoch_id: int):
    if df.count() == 0:
        return

    # Статистика по хостам (исходящий и входящий трафик)
    src_stats = df.groupBy("window_start", "src_ip") \
        .agg(_sum("packet_count").alias("packet_count"),
             _sum("byte_sum").alias("byte_sum")) \
        .withColumn("direction", lit(0)) \
        .withColumnRenamed("src_ip", "host_ip")
    
    dst_stats = df.groupBy("window_start", "dst_ip") \
        .agg(_sum("packet_count").alias("packet_count"),
             _sum("byte_sum").alias("byte_sum")) \
        .withColumn("direction", lit(1)) \
        .withColumnRenamed("dst_ip", "host_ip")
    
    host_stats = src_stats.union(dst_stats)
    host_stats.select("window_start", "host_ip", "direction", "packet_count", "byte_sum") \
        .write.jdbc(url=CLICKHOUSE_URL, table="traffic_stats_by_host", mode="append", properties=JDBC_PROPS)

    # Статистика по протоколам
    protocol_stats = df.groupBy("window_start", "protocol") \
        .agg(_sum("packet_count").alias("packet_count"),
             _sum("byte_sum").alias("byte_sum"))
    protocol_stats.write.jdbc(url=CLICKHOUSE_URL, table="traffic_stats_by_protocol", mode="append", properties=JDBC_PROPS)

    # Статистика по портам (только TCP/UDP, порт > 0)
    port_stats = df.filter(col("src_port") > 0) \
        .groupBy("window_start", "src_port") \
        .agg(_sum("packet_count").alias("packet_count"),
             _sum("byte_sum").alias("byte_sum")) \
        .withColumnRenamed("src_port", "port")
    port_stats.write.jdbc(url=CLICKHOUSE_URL, table="traffic_stats_by_port", mode="append", properties=JDBC_PROPS)

def read_recent_stats(spark, minutes: int):
    query = f"""
        SELECT window_start, src_ip, dst_ip, src_port, dst_port,
               protocol, direction, packet_count, byte_sum
        FROM traffic_stats
        WHERE window_start >= now() - INTERVAL {minutes} MINUTE
    """
    return spark.read.jdbc(url=CLICKHOUSE_URL, table=f"({query})", properties=JDBC_PROPS)