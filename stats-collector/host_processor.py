from pyspark.sql import DataFrame
from config import CLICKHOUSE_JDBC_URL, JDBC_PROPS


def write_hosts(df: DataFrame, epoch_id: int):
    """
    ReplacingMergeTree(register_ts) схлопнет дубли по host_id.
    """
    if df.rdd.isEmpty():
        return
    df.select(
        "host_id", "hostname", "os", "arch",
        "kernel_version", "interfaces", "boot_time_sec", "register_ts",
    ).write \
        .format("jdbc") \
        .option("url", CLICKHOUSE_JDBC_URL) \
        .options(**JDBC_PROPS) \
        .option("dbtable", "hosts_info") \
        .mode("append") \
        .save()