"""Конвейер: окно -> детекторы -> агрегированный risk -> Detection[]."""
from __future__ import annotations

import logging

from analyzer.config import Config
from analyzer.detectors import Detection, Detector, Features, Severity, build_detectors

logger = logging.getLogger(__name__)


class Pipeline:
    """Прогоняет фичи закрытого окна через все активные детекторы."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.detectors: list[Detector] = build_detectors(cfg)
        logger.info("pipeline detectors: %s", [d.name for d in self.detectors])

    def process(self, features: Features) -> list[Detection]:
        detections: list[Detection] = []
        for det in self.detectors:
            try:
                detections.extend(det.score(features))
            except Exception as exc:  # noqa: BLE001
                logger.error("detector %s failed: %s", det.name, exc)
        return detections

    def combined_risk(self, detections: list[Detection]) -> float:
        """Взвешенная агрегация risk_score правил и ML в [0,1]."""
        if not detections:
            return 0.0
        rule_scores = [d.risk_score for d in detections if d.detector.startswith("rule")]
        ml_scores = [d.risk_score for d in detections
                     if d.detector.startswith(("ml", "nn"))]
        rw, mw = self.cfg.analyzer.rule_weight, self.cfg.analyzer.ml_weight
        rule = max(rule_scores) if rule_scores else 0.0
        ml = max(ml_scores) if ml_scores else 0.0
        denom = (rw if rule_scores else 0) + (mw if ml_scores else 0)
        if denom == 0:
            return 0.0
        return round((rule * rw + ml * mw) / denom, 4)
