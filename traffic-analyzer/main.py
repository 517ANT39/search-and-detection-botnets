"""Точка входа анализатора."""
from __future__ import annotations

import logging
import signal
import sys

from analyzer.config import Config
from analyzer.consumer import AnalyzerConsumer


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> None:
    cfg = Config.load("config.yaml")
    setup_logging(cfg.log_level)
    log = logging.getLogger("main")

    consumer = AnalyzerConsumer(cfg)

    def handle_signal(signum, _frame):  # noqa: ANN001
        log.info("received signal %s, stopping...", signum)
        consumer.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    log.info("analyzer starting: brokers=%s topic=%s detectors=%s",
             cfg.kafka.brokers, cfg.kafka.packets_topic, cfg.analyzer.detectors)
    try:
        consumer.start()
    except Exception as exc:  # noqa: BLE001
        log.exception("fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
