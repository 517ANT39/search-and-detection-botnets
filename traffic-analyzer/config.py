"""Загрузка и валидация конфигурации анализатора."""
from __future__ import annotations

import os
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class KafkaConfig(BaseModel):
    brokers: list[str] = Field(default_factory=lambda: ["127.0.0.1:9092"])
    group_id: str = "traffic-analyzer"
    packets_topic: str = "traffic.packets"
    hosts_topic: str = "traffic.hosts"
    # ── топики результатов анализа (публикует анализатор, читает ClickHouse) ──
    alerts_topic: str = "traffic.alerts"
    profiles_topic: str = "traffic.profiles"
    poll_timeout: float = 1.0
    auto_offset_reset: Literal["earliest", "latest"] = "latest"


class WindowConfig(BaseModel):
    tumbling_sec: int = 60
    sliding_sec: int = 300
    sliding_step_sec: int = 60
    session_timeout_sec: int = 120
    watermark_sec: int = 30


class Thresholds(BaseModel):
    pps: float = 10_000.0
    bps: float = 100_000_000.0  # 100 Mbps
    uniq_dst_port_scan: int = 100
    uniq_dst_ip_scan: int = 100
    beacon_std_max: float = 0.5
    beacon_min_conns: int = 5


class AnalyzerConfig(BaseModel):
    detectors: list[str] = Field(default_factory=lambda: ["rule", "isoforest"])
    ml_core: str = "isoforest"
    thresholds: Thresholds = Field(default_factory=Thresholds)
    rule_weight: float = 0.6
    ml_weight: float = 0.4


class ClickHouseConfig(BaseModel):
    """Используется ТОЛЬКО для чтения (train.py, second_pass.py). Запись идёт в Kafka."""
    host: str = "127.0.0.1"
    port: int = 8123
    database: str = "traffic"
    user: str = "traffic"
    password: str = "traffic_pass"


class ModelConfig(BaseModel):
    path: str = "models/isoforest.joblib"
    version: str = "v1"


class Config(BaseModel):
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    windows: WindowConfig = Field(default_factory=WindowConfig)
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    clickhouse: ClickHouseConfig = Field(default_factory=ClickHouseConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    log_level: str = "INFO"

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        """Загружает конфиг из YAML, поверх — переопределения из env (ANALYZER_*)."""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        cfg = cls(**data)

        if brokers := os.getenv("ANALYZER_KAFKA_BROKERS"):
            cfg.kafka.brokers = [b.strip() for b in brokers.split(",")]
        if group := os.getenv("ANALYZER_KAFKA_GROUP"):
            cfg.kafka.group_id = group
        if ch_host := os.getenv("ANALYZER_CH_HOST"):
            cfg.clickhouse.host = ch_host
        if ch_pass := os.getenv("ANALYZER_CH_PASSWORD"):
            cfg.clickhouse.password = ch_pass
        if lvl := os.getenv("ANALYZER_LOG_LEVEL"):
            cfg.log_level = lvl

        return cfg
