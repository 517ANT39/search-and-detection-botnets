from pydantic import BaseModel, Field
from typing import Optional, Dict

class HostInfo(BaseModel):
    host_id: str
    hostname: str
    os: str
    arch: str
    kernel_version: str
    interfaces: Dict[int, str]
    boot_time_sec: int
    register_ts: int

class AlertOut(BaseModel):
    timestamp: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    direction: int
    packet_count: int
    byte_sum: int
    threshold_count: float
    threshold_bytes: float
    anomaly_type: str
    host_id: Optional[str] = ""

class FilterCreate(BaseModel):
    name: str
    filter_data: dict

class FilterOut(BaseModel):
    id: int
    name: str
    filter_data: dict
    created_at: str

class TrafficPoint(BaseModel):
    timestamp: str
    packets: int
    bytes: int

class TopologyLink(BaseModel):
    src: str
    dst: str
    packets: int
    bytes: int