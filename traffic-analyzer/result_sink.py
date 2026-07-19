"""Публикация результатов анализа (профили и алерты) в Kafka.

Формат — JSON-объект на сообщение (JSONEachRow), совместим с ClickHouse Kafka Engine.
Анализатор НЕ пишет в ClickHouse напрямую; чтение из Kafka выполняет сам ClickHouse.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from confluent_kafka import Producer

from analyzer.config import Config
from analyzer.detectors import Detection, Features

logger = logging.getLogger(__name__)


def _iso(ts: float) -> str:
    """Event-time (сек) → ISO-8601 UTC, парсится ClickHouse в DateTime64."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


class KafkaResultSink:
    """Пишет профили и алерты в Kafka. Интерфейс совместим с прежним ClickHouseSink."""

    def __init__(self, cfg: Config) -> None:
        self.alerts_topic = cfg.kafka.alerts_topic
        self.profiles_topic = cfg.kafka.profiles_topic
        self._producer = Producer({
            "bootstrap.servers": ",".join(cfg.kafka.brokers),
            "compression.type": "snappy",
            "linger.ms": 50,
            "batch.num.messages": 1000,
            "queue.buffering.max.messages": 200_000,
        })

    # ── профили окон ──
    def add_profile(self, f: Features) -> None:
        payload = {
            "host_id": f.host_id,
            "window_start": _iso(f.window_start),
            "window_end": _iso(f.window_end),
            "window_type": f.window_type,          # tumbling|sliding|session (Enum по строке)
            "packets": f.packets,
            "bytes": f.bytes,
            "pps": f.pps,
            "bps": f.bps,
            "uniq_dst_ip": f.uniq_dst_ip,
            "uniq_dst_port": f.uniq_dst_port,
            "proto_tcp": f.proto_tcp,
            "proto_udp": f.proto_udp,
            "proto_other": f.proto_other,
            "conn_interval_avg": f.conn_interval_avg,
            "conn_interval_std": f.conn_interval_std,
        }
        self._produce(self.profiles_topic, f.host_id, payload)

    # ── алерты ──
    def add_alert(self, d: Detection) -> None:
        payload = {
            "alert_id": d.alert_id(),
            "host_id": d.host_id,
            "detected_at": _iso(d.window_start),
            "window_start": _iso(d.window_start),
            "detector": d.detector,
            "category": d.category,
            "severity": int(d.severity),           # UInt8 (1..4) → Enum на стороне CH
            "risk_score": d.risk_score,
            "model_version": d.model_version,
            "details": json.dumps(d.details, ensure_ascii=False),
        }
        self._produce(self.alerts_topic, d.host_id, payload)

    def _produce(self, topic: str, key: str, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        try:
            self._producer.produce(topic, key=key.encode(), value=data)
            self._producer.poll(0)
        except BufferError:
            logger.warning("producer buffer full, flushing")
            self._producer.flush(5)
            self._producer.produce(topic, key=key.encode(), value=data)

    def maybe_flush(self) -> None:
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush(10)

    def close(self) -> None:
        logger.info("flushing kafka result producer")
        self._producer.flush(15)
