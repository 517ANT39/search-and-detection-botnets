from pyspark.sql import DataFrame
from config import CLICKHOUSE_JDBC_URL, JDBC_PROPS


def _write(df: DataFrame, table: str, columns: list):
    if df.rdd.isEmpty():
        return
    df.select(*columns).write \
        .format("jdbc") \
        .option("url", CLICKHOUSE_JDBC_URL) \
        .options(**JDBC_PROPS) \
        .option("dbtable", table) \
        .mode("append") \
        .save()


def write_base(df):
    _write(df, "traffic_stats", [
        "window_start", "src_ip", "dst_ip", "src_port", "dst_port",
        "protocol", "direction", "packet_count", "byte_sum",
    ])

def write_by_protocol(df):
    _write(df, "traffic_stats_by_protocol",
           ["window_start", "protocol", "packet_count", "byte_sum"])

def write_by_port(df):
    _write(df, "traffic_stats_by_port",
           ["window_start", "port", "port_type", "packet_count", "byte_sum"])

def write_by_direction(df):
    _write(df, "traffic_stats_by_direction",
           ["window_start", "direction", "packet_count", "byte_sum"])

def write_by_host(df):
    _write(df, "traffic_stats_by_host",
           ["window_start", "host_ip", "role", "packet_count", "byte_sum"])

def write_by_subnet(df):
    _write(df, "traffic_stats_by_subnet",
           ["window_start", "src_subnet", "dst_subnet", "packet_count", "byte_sum"])

def write_by_pair(df):
    _write(df, "traffic_stats_by_pair",
           ["window_start", "src_ip", "dst_ip", "protocol", "packet_count", "byte_sum"])

def write_top_sources(df):
    _write(df, "traffic_top_sources",
           ["window_start", "src_ip", "packet_count", "byte_sum", "rank"])

def write_top_targets(df):
    _write(df, "traffic_top_targets",
           ["window_start", "dst_ip", "packet_count", "byte_sum", "rank"])