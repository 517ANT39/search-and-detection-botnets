from pyspark.sql import DataFrame
from pyspark.sql.functions import col, concat_ws, struct, to_json
from config import KAFKA_BOOTSTRAP, ALERT_TOPIC


def publish_alerts(alerts: DataFrame):
    payload = alerts.select(
        concat_ws(":",
            col("detector"), col("view"),
            col("src_ip"), col("src_port").cast("string"),
            col("dst_ip"), col("dst_port").cast("string"),
            col("protocol").cast("string"),
        ).alias("key"),
        to_json(struct("*")).alias("value"),
    )

    (payload.write
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("topic", ALERT_TOPIC)
        .mode("append")
        .save())