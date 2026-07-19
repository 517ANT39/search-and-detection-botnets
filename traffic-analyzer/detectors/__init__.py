"""Реестр детекторов и фабрика выбора ядра по имени."""
from __future__ import annotations

from analyzer.config import Config
from analyzer.detectors.base import Detection, Detector, Features, Severity
from analyzer.detectors.experimental import (
    KMeansDetector,
    LOFDetector,
    MLPDetector,
    OCSVMDetector,
)
from analyzer.detectors.isoforest import IsolationForestDetector
from analyzer.detectors.rules import RuleDetector
from analyzer.detectors.zscore import ZScoreDetector

__all__ = [
    "Detection", "Detector", "Features", "Severity",
    "build_detectors", "build_ml_detector",
]


def build_ml_detector(name: str, cfg: Config) -> Detector:
    """Создаёт ML-детектор по имени ядра (для рантайма, обучения и бенчмарка)."""
    mv = cfg.model.version
    path = cfg.model.path
    match name:
        case "isoforest":
            return IsolationForestDetector(path, mv)
        case "zscore":
            return ZScoreDetector()
        case "lof":
            return LOFDetector(path, mv)
        case "ocsvm":
            return OCSVMDetector(path, mv)
        case "kmeans":
            return KMeansDetector(path, mv)
        case "mlp":
            return MLPDetector(path, mv)
        case _:
            raise ValueError(f"unknown ML detector: {name!r}")


def build_detectors(cfg: Config) -> list[Detector]:
    """Собирает активный конвейер детекторов согласно конфигу."""
    detectors: list[Detector] = []
    for name in cfg.analyzer.detectors:
        if name == "rule":
            detectors.append(RuleDetector(cfg.analyzer.thresholds))
        elif name == "zscore":
            detectors.append(ZScoreDetector())
        else:
            # ML-ядра создаются через фабрику
            detectors.append(build_ml_detector(name, cfg))
    return detectors
