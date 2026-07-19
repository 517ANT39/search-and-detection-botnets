"""Синхронный confluent-kafka consumer: обработка по мере прихода."""
from __future__ import annotations

import logging

from confluent_kafka import Consumer, KafkaError, KafkaException

from analyzer.config import Config
from analyzer.features import iter_events
from analyzer.gen import traffic_pb2
from analyzer.pipeline import Pipeline
from analyzer.result_sink import KafkaResultSink
from analyzer.windowing import WindowManager

logger = logging.getLogger(__name__)


class AnalyzerConsumer:
    """Читает PacketBatch из Kafka, гоняет через окна и детекторы, публикует в Kafka."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.pipeline = Pipeline(cfg)
        self.sink = KafkaResultSink(cfg)
        self.windows = WindowManager(
            tumbling_sec=cfg.windows.tumbling_sec,
            sliding_sec=cfg.windows.sliding_sec,
            sliding_step_sec=cfg.windows.sliding_step_sec,
            session_timeout_sec=cfg.windows.session_timeout_sec,
            watermark_sec=cfg.windows.watermark_sec,
        )
        self._running = False
        self._consumer = Consumer({
            "bootstrap.servers": ",".join(cfg.kafka.brokers),
            "group.id": cfg.kafka.group_id,
            "auto.offset.reset": cfg.kafka.auto_offset_reset,
            "enable.auto.commit": False,   # at-least-once: коммит вручную
        })

    def start(self) -> None:
        self._consumer.subscribe([self.cfg.kafka.packets_topic])
        self._running = True
        logger.info("consumer subscribed to %s", self.cfg.kafka.packets_topic)
        self._loop()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        try:
            while self._running:
                msg = self._consumer.poll(self.cfg.kafka.poll_timeout)
                if msg is None:
                    self.sink.maybe_flush()
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    raise KafkaException(msg.error())

                self._handle(msg.value())
                # at-least-once: коммит offset ПОСЛЕ успешной обработки
                self._consumer.commit(msg, asynchronous=False)
                self.sink.maybe_flush()
        finally:
            self._shutdown()

    def _handle(self, payload: bytes) -> None:
        batch = traffic_pb2.PacketBatch()
        try:
            batch.ParseFromString(payload)
        except Exception as exc:  # noqa: BLE001
            logger.error("bad protobuf message, skipping: %s", exc)
            return

        for event in iter_events(batch):
            closed = self.windows.add_event(
                event.host_id, event.ts, event.dst_ip,
                event.dst_port, event.pkt_len, event.protocol,
            )
            for features in closed:
                self.sink.add_profile(features)
                for det in self.pipeline.process(features):
                    self.sink.add_alert(det)

    def _shutdown(self) -> None:
        logger.info("shutting down consumer (late_events=%d)",
                    self.windows.late_events)
        for features in self.windows.flush_all():
            self.sink.add_profile(features)
            for det in self.pipeline.process(features):
                self.sink.add_alert(det)
        self.sink.close()
        self._consumer.close()
