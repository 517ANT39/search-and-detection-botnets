"""Базовые абстракции детекторов — сменное ядро анализа."""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass
class Features:
    """Вектор признаков одного закрытого окна для одного хоста."""
    host_id: str
    window_start: float          # event-time, секунды (unix)
    window_end: float
    window_type: str             # tumbling | sliding | session
    packets: int
    bytes: int
    pps: float
    bps: float
    uniq_dst_ip: int
    uniq_dst_port: int
    proto_tcp: int
    proto_udp: int
    proto_other: int
    conn_interval_avg: float
    conn_interval_std: float

    def to_vector(self) -> list[float]:
        """Числовой вектор для ML-детекторов (порядок фиксирован)."""
        return [
            float(self.packets),
            float(self.bytes),
            self.pps,
            self.bps,
            float(self.uniq_dst_ip),
            float(self.uniq_dst_port),
            float(self.proto_tcp),
            float(self.proto_udp),
            float(self.proto_other),
            self.conn_interval_avg,
            self.conn_interval_std,
        ]

    @staticmethod
    def vector_names() -> list[str]:
        return [
            "packets", "bytes", "pps", "bps", "uniq_dst_ip", "uniq_dst_port",
            "proto_tcp", "proto_udp", "proto_other",
            "conn_interval_avg", "conn_interval_std",
        ]


@dataclass
class Detection:
    """Результат срабатывания детектора."""
    host_id: str
    window_start: float
    window_end: float
    detector: str            # 'rule:port_scan' | 'ml:isoforest' | 'nn:mlp'
    category: str            # scan | c2 | exfil | dos | anomaly
    severity: Severity
    risk_score: float        # [0, 1]
    model_version: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def alert_id(self) -> str:
        """Детерминированный идемпотентный ключ инцидента."""
        raw = f"{self.host_id}|{int(self.window_start)}|{self.detector}"
        return hashlib.sha1(raw.encode()).hexdigest()


class Detector(ABC):
    """Единый контракт для правил, ML и нейросетевых ядер."""

    name: str = "base"
    model_version: str = ""

    def fit(self, X: list[list[float]]) -> None:  # noqa: N803
        """Обучение (no-op для правил). X — список векторов фич."""
        return None

    @abstractmethod
    def score(self, features: Features) -> list[Detection]:
        """Оценивает окно и возвращает список обнаружений (возможно пустой)."""
        raise NotImplementedError
