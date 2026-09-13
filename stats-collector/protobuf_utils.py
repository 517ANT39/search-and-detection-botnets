import models.traffic_send_analyze_pb2 as analyze_pb
import models.host_info_pb2 as host_info_pb
from pyspark.sql.types import StructType, StructField, LongType, StringType, IntegerType
import json
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
    
HOST_SCHEMA = StructType([
    StructField("host_id",        StringType(), True),
    StructField("hostname",       StringType(), True),
    StructField("os",             StringType(), True),
    StructField("arch",           StringType(), True),
    StructField("kernel_version", StringType(), True),
    StructField("interfaces",     StringType(), True),
    StructField("boot_time_sec",  LongType(),   True),
    StructField("register_ts",    LongType(),   True),
])


def decode_host(pb_bytes: bytes) -> dict:
    h = host_info_pb.HostInfo()
    h.ParseFromString(pb_bytes)
    return {
        "host_id":        h.host_id,
        "hostname":       h.hostname,
        "os":             h.os,
        "arch":           h.arch,
        "kernel_version": h.kernel_version,
        "interfaces":     json.dumps(dict(h.interfaces)),
        "boot_time_sec":  h.boot_time_sec,
        "register_ts":    h.register_ts,
    }
