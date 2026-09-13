# feature_extraction.py
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, when, log1p, lit

def add_features(df: DataFrame) -> DataFrame:
    """
    Добавляет колонки признаков для модели:
      - packet_count (уже есть)
      - byte_sum (уже есть)
      - avg_packet_size = byte_sum / packet_count (если packet_count>0, иначе 0)
      - log_packet_count = log1p(packet_count)
      - log_byte_sum = log1p(byte_sum)
    Возвращает DataFrame с дополнительными колонками.
    """
    return df.withColumn(
        "avg_packet_size",
        when(col("packet_count") > 0, col("byte_sum") / col("packet_count")).otherwise(0)
    ).withColumn(
        "log_packet_count",
        log1p(col("packet_count"))
    ).withColumn(
        "log_byte_sum",
        log1p(col("byte_sum"))
    )

# Список признаков, используемых моделью
FEATURE_COLUMNS = [
    "packet_count",
    "byte_sum",
    "avg_packet_size",
    "log_packet_count",
    "log_byte_sum"
]