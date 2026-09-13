from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, window, count, sum as _sum, lit, regexp_extract, row_number
)
from pyspark.sql.window import Window


def base_5tuple(df: DataFrame) -> DataFrame:
    """5-tuple + direction × 1 минута — базовая агрегация."""
    return (
        df.withWatermark("timestamp", "1 minute")
          .groupBy(
              window("timestamp", "1 minute", "1 minute"),
              "src_ip", "dst_ip", "src_port", "dst_port",
              "protocol", "direction",
          )
          .agg(
              count("*").alias("packet_count"),
              _sum("pkt_len").alias("byte_sum"),
          )
          .withColumn("window_start", col("window.start").cast("timestamp"))
          .drop("window")
    )


def by_protocol(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("window_start", "protocol")
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
    )


def by_port(df: DataFrame) -> DataFrame:
    src = (
        df.filter(col("src_port") > 0)
          .groupBy("window_start", col("src_port").alias("port"))
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
          .withColumn("port_type", lit("src"))
    )
    dst = (
        df.filter(col("dst_port") > 0)
          .groupBy("window_start", col("dst_port").alias("port"))
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
          .withColumn("port_type", lit("dst"))
    )
    return src.union(dst)


def by_direction(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("window_start", "direction")
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
    )


def by_host(df: DataFrame) -> DataFrame:
    src = (
        df.groupBy("window_start", col("src_ip").alias("host_ip"))
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
          .withColumn("role", lit("src"))
    )
    dst = (
        df.groupBy("window_start", col("dst_ip").alias("host_ip"))
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
          .withColumn("role", lit("dst"))
    )
    return src.union(dst)


def by_subnet(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("src_subnet", regexp_extract(col("src_ip"), r"^(\d+\.\d+\.\d+)\.", 1))
          .withColumn("dst_subnet", regexp_extract(col("dst_ip"), r"^(\d+\.\d+\.\d+)\.", 1))
          .groupBy("window_start", "src_subnet", "dst_subnet")
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
    )


def by_pair(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("window_start", "src_ip", "dst_ip", "protocol")
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
    )


def top_sources(df: DataFrame, top_n: int = 10) -> DataFrame:
    agg = (
        df.groupBy("window_start", "src_ip")
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
    )
    w = Window.partitionBy("window_start").orderBy(col("packet_count").desc())
    return agg.withColumn("rank", row_number().over(w)).filter(col("rank") <= top_n)


def top_targets(df: DataFrame, top_n: int = 10) -> DataFrame:
    agg = (
        df.groupBy("window_start", "dst_ip")
          .agg(
              _sum("packet_count").alias("packet_count"),
              _sum("byte_sum").alias("byte_sum"),
          )
    )
    w = Window.partitionBy("window_start").orderBy(col("packet_count").desc())
    return agg.withColumn("rank", row_number().over(w)).filter(col("rank") <= top_n)