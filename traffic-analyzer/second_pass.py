"""Второй проход: доп. ML-анализ накопленных профилей из ClickHouse.

Читает профили из ClickHouse (чтение разрешено), результаты публикует в Kafka.
"""
from __future__ import annotations

import argparse
import logging

import clickhouse_connect

from analyzer.config import Config
from analyzer.detectors import build_ml_detector
from analyzer.detectors.base import Features
from analyzer.result_sink import KafkaResultSink

logger = logging.getLogger(__name__)


def _row_to_features(row: dict) -> Features:
    wtype_map = {1: "tumbling", 2: "sliding", 3: "session"}
    wt = row["window_type"]
    if isinstance(wt, int):
        wt = wtype_map.get(wt, "tumbling")
    return Features(
        host_id=row["host_id"],
        window_start=row["window_start"].timestamp(),
        window_end=row["window_end"].timestamp(),
        window_type=wt,
        packets=row["packets"], bytes=row["bytes"],
        pps=row["pps"], bps=row["bps"],
        uniq_dst_ip=row["uniq_dst_ip"], uniq_dst_port=row["uniq_dst_port"],
        proto_tcp=row["proto_tcp"], proto_udp=row["proto_udp"],
        proto_other=row["proto_other"],
        conn_interval_avg=row["conn_interval_avg"],
        conn_interval_std=row["conn_interval_std"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Second-pass deep analysis")
    parser.add_argument("--core", default=None)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s")
    cfg = Config.load(args.config)
    core = args.core or cfg.analyzer.ml_core

    client = clickhouse_connect.get_client(
        host=cfg.clickhouse.host, port=cfg.clickhouse.port,
        database=cfg.clickhouse.database,
        username=cfg.clickhouse.user, password=cfg.clickhouse.password,
    )
    query = f"""
        SELECT host_id, window_start, window_end, window_type,
               packets, bytes, pps, bps, uniq_dst_ip, uniq_dst_port,
               proto_tcp, proto_udp, proto_other,
               conn_interval_avg, conn_interval_std
        FROM host_profiles FINAL
        WHERE window_start >= now() - INTERVAL {args.hours} HOUR
    """
    result = client.query(query)
    rows = [dict(zip(result.column_names, r)) for r in result.result_rows]
    client.close()

    detector = build_ml_detector(core, cfg)
    sink = KafkaResultSink(cfg)
    found = 0
    for row in rows:
        for det in detector.score(_row_to_features(row)):
            sink.add_alert(det)
            found += 1
    sink.close()
    logger.info("second pass complete: analyzed=%d found=%d core=%s",
                len(rows), found, core)


if __name__ == "__main__":
    main()
