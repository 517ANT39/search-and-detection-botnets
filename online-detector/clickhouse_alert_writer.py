from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit
from config import CLICKHOUSE_JDBC_URL, JDBC_PROPS

ALERT_COLUMNS = [
    "timestamp", "detector", "view",
    "src_ip", "src_port", "dst_ip", "dst_port", "protocol",
    "direction",
    "packet_count", "byte_sum",
    "active_minutes", "avg_per_min",
    "baseline_value", "baseline_stddev", "z_score",
    "anomaly_type", "severity",
    "host_id",
]


def write_alerts(df: DataFrame):
    out = df
    if "direction" not in out.columns:
        out = out.withColumn("direction", lit(-1).cast("int"))
    if "host_id" not in out.columns:
        out = out.withColumn("host_id", lit(""))

    out = (
        out
        .withColumn("src_port",       col("src_port").cast("int"))
        .withColumn("dst_port",       col("dst_port").cast("int"))
        .withColumn("protocol",       col("protocol").cast("int"))
        .withColumn("direction",      col("direction").cast("int"))
        .withColumn("packet_count",   col("packet_count").cast("long"))
        .withColumn("byte_sum",       col("byte_sum").cast("long"))
        .withColumn("active_minutes", col("active_minutes").cast("int"))
        .withColumn("avg_per_min",    col("avg_per_min").cast("double"))
        .withColumn("baseline_value", col("baseline_value").cast("double"))
        .withColumn("baseline_stddev",col("baseline_stddev").cast("double"))
        .withColumn("z_score",        col("z_score").cast("double"))
    )

    (out.select(*ALERT_COLUMNS)
        .write.format("jdbc")
        .option("url", CLICKHOUSE_JDBC_URL)
        .options(**JDBC_PROPS)
        .option("dbtable", "alerts")
        .mode("append")
        .save())