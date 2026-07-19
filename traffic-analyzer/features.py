"""Преобразование protobuf PacketBatch в поток событий для оконного менеджера."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class Event:
    host_id: str
    ts: float          # event-time, секунды
    dst_ip: int
    dst_port: int
    pkt_len: int
    protocol: int


def iter_events(batch) -> Iterator[Event]:  # batch: traffic_pb2.PacketBatch
    """Разворачивает PacketBatch в отдельные события."""
    host_id = batch.host_id
    for evt in batch.events:
        yield Event(
            host_id=host_id,
            ts=evt.timestamp_ns / 1e9,   # ns -> s
            dst_ip=evt.dst_ip,
            dst_port=evt.dst_port,
            pkt_len=evt.pkt_len,
            protocol=evt.protocol,
        )
