import models.traffic_send_analyze_pb2 as analyze_pb
from pyspark.sql.types import StructType, StructField, LongType, StringType, IntegerType

# Схема для DataFrame после десериализации
PACKET_SCHEMA = StructType([
    StructField("timestamp_ns", LongType(), True),
    StructField("src_ip", StringType(), True),
    StructField("dst_ip", StringType(), True),
    StructField("src_port", IntegerType(), True),
    StructField("dst_port", IntegerType(), True),
    StructField("pkt_len", IntegerType(), True),
    StructField("protocol", IntegerType(), True),   # enum -> int
    StructField("hook", IntegerType(), True),
    StructField("direction", IntegerType(), True),
    StructField("ifindex", IntegerType(), True),
    StructField("host_id", StringType(), True),
])

def decode_packet(pb_bytes: bytes) -> dict:
    """Декодирует Protobuf-сообщение PacketInfo в словарь."""
    p = analyze_pb.PacketInfo()
    p.ParseFromString(pb_bytes)
    return {
        "timestamp_ns": p.timestamp_ns,
        "src_ip": p.src_ip,
        "dst_ip": p.dst_ip,
        "src_port": p.src_port,
        "dst_port": p.dst_port,
        "pkt_len": p.pkt_len,
        "protocol": p.protocol,
        "hook": p.hook,
        "direction": p.direction,
        "ifindex": p.ifindex,
        "host_id": p.host_id,
    }