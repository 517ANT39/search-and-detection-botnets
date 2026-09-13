from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, window, count, sum as _sum

from config import (
    KAFKA_BOOTSTRAP, PACKETS_TOPIC,SPARK_CLUSTER ,
    WINDOW_DURATION, SLIDE_DURATION, WATERMARK_DELAY, TRIGGER_INTERVAL,
)
from protobuf_utils import decode_packet, PACKET_SCHEMA
from detector import detect_all_views
from alert_publisher import publish_alerts
from clickhouse_alert_writer import write_alerts



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
def process_batch(df, epoch_id):
    """
    df — агрегат по 5-tuple внутри скользящего окна.
    Всё, что делаем — статистика внутри окна. Никаких чтений из БД.
    """
    try:
        spark = df.sparkSession
        alerts = detect_all_views(df, spark)

        # В ClickHouse
        try:
            write_alerts(alerts)
        except Exception as e:
            print(f"[batch {epoch_id}] CH ошибка: {e}")

        # В Kafka
        try:
            publish_alerts(alerts)
        except Exception as e:
            print(f"[batch {epoch_id}] Kafka ошибка: {e}")

    except Exception as e:
        print(f"[batch {epoch_id}] ошибка: {e}")
        import traceback; traceback.print_exc()


def main():
    spark = build_spark()
    decode_udf = udf(decode_packet, PACKET_SCHEMA)

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", PACKETS_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    packets = (
        raw
        .select(decode_udf(col("value")).alias("p"))
        .select("p.*")
        .withColumn("timestamp", (col("timestamp_ns") / 1e9).cast("timestamp"))
    )

    # Скользящее окно 5 мин с шагом 1 мин — единственный источник данных
    windowed = (
        packets
        .withWatermark("timestamp", WATERMARK_DELAY)
        .groupBy(
            window("timestamp", WINDOW_DURATION, SLIDE_DURATION),
            "src_ip", "src_port", "dst_ip", "dst_port", "protocol",
        )
        .agg(
            count("*").alias("packet_count"),
            _sum("pkt_len").alias("byte_sum"),
        )
        .withColumn("window_start", col("window.start").cast("timestamp"))
        .drop("window")
    )

    query = (
        windowed.writeStream
        .foreachBatch(process_batch)
        .outputMode("append")
        .trigger(processingTime=TRIGGER_INTERVAL)
        .option("checkpointLocation", "/tmp/checkpoints/analyzer")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()