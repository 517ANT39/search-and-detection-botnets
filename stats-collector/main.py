from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf

from config import (
    KAFKA_BOOTSTRAP, TRAFFIC_TOPIC, HOST_TOPIC, TOP_N,SPARK_CLUSTER
)
from protobuf_utils import (
    decode_packet, decode_host, PACKET_SCHEMA, HOST_SCHEMA,
)
from aggregators import (
    base_5tuple, by_protocol, by_port, by_direction,
    by_host, by_subnet, by_pair, top_sources, top_targets,
)
from clickhouse_writer import (
    write_base, write_by_protocol, write_by_port, write_by_direction,
    write_by_host, write_by_subnet, write_by_pair,
    write_top_sources, write_top_targets,
)
from host_processor import write_hosts




def build_spark():
    return (
         SparkSession.builder \
        .appName("TrafficAnomalyEnsemble") 
        .master(SPARK_CLUSTER) 
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0,com.clickhouse:clickhouse-jdbc:0.10.0") 
        .config("spark.sql.shuffle.partitions", 200) 
        .config("spark.sql.streaming.statefulOperator.checkCorrectness.enabled", "false") 
        .getOrCreate()
    )


def process_traffic_batch(df, epoch_id):
    """
    Один microbatch = одно окно.
    df уже содержит: window_start, 5-tuple, direction, packet_count, byte_sum.
    Из него считаем все срезы.
    """
    if df.rdd.isEmpty():
        return

    try:
        # 1. Базовая таблица
        write_base(df)

        # 2. Rollup'ы
        write_by_protocol(by_protocol(df))
        write_by_port(by_port(df))
        write_by_direction(by_direction(df))
        write_by_host(by_host(df))
        write_by_subnet(by_subnet(df))
        write_by_pair(by_pair(df))

        # 3. Top-N
        write_top_sources(top_sources(df, top_n=TOP_N))
        write_top_targets(top_targets(df, top_n=TOP_N))

    except Exception as e:
        print(f"[batch {epoch_id}] ошибка: {e}")


def main():
    spark = build_spark()

    packet_udf = udf(decode_packet, PACKET_SCHEMA)
    host_udf   = udf(decode_host,   HOST_SCHEMA)

    # --- Пакеты ---
    raw_traffic = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TRAFFIC_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )
    packets = (
        raw_traffic
        .select(packet_udf(col("value")).alias("p"))
        .select("p.*")
        .withColumn("timestamp", (col("timestamp_ns") / 1e9).cast("timestamp"))
    )
    base_df = base_5tuple(packets)

    traffic_query = (
        base_df.writeStream
        .foreachBatch(process_traffic_batch)
        .outputMode("append")
        .trigger(processingTime="1 minute")
        .option("checkpointLocation", "/tmp/checkpoints/traffic")
        .start()
    )

    # --- HostInfo ---
    raw_hosts = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", HOST_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )
    hosts = (
        raw_hosts
        .select(host_udf(col("value")).alias("h"))
        .select("h.*")
    )
    host_query = (
        hosts.writeStream
        .foreachBatch(write_hosts)
        .outputMode("append")
        .trigger(processingTime="30 seconds")
        .option("checkpointLocation", "/tmp/checkpoints/hosts")
        .start()
    )

    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()