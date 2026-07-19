"""ML-ядро на Isolation Forest (scikit-learn)."""
from __future__ import annotations

import logging
import os

import joblib
import numpy as np

from analyzer.detectors.base import Detection, Detector, Features, Severity

logger = logging.getLogger(__name__)


class IsolationForestDetector(Detector):
    """Обнаружение аномалий без меток. Обучается офлайн, в рантайме — инференс."""

    name = "isoforest"

    def __init__(self, model_path: str, model_version: str = "v1",
                 contamination: float = 0.02) -> None:
        self.model_path = model_path
        self.model_version = model_version
        self.contamination = contamination
        self._model = None
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.model_path):
            try:
                self._model = joblib.load(self.model_path)
                logger.info("isoforest model loaded from %s", self.model_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("failed to load isoforest model: %s", exc)
                self._model = None
        else:
            logger.warning("isoforest model not found at %s — detector inactive "
                           "until trained", self.model_path)

    def fit(self, X: list[list[float]]) -> None:  # noqa: N803
        from sklearn.ensemble import IsolationForest

        arr = np.asarray(X, dtype=float)
        if arr.size == 0:
            logger.warning("isoforest.fit: empty training set")
            return
        model = IsolationForest(
            n_estimators=200,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(arr)
        self._model = model
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        joblib.dump(model, self.model_path)
        logger.info("isoforest trained on %d samples, saved to %s",
                    len(X), self.model_path)

    def score(self, f: Features) -> list[Detection]:
        if self._model is None:
            return []

        vec = np.asarray([f.to_vector()], dtype=float)
        # decision_function: чем меньше (отрицательнее), тем аномальнее
        raw = float(self._model.decision_function(vec)[0])
        is_anomaly = self._model.predict(vec)[0] == -1
        if not is_anomaly:
            return []

        # Нормализуем в [0,1]: типичный decision_function ∈ [-0.5, 0.5]
        risk = float(np.clip(0.5 - raw, 0.0, 1.0))
        severity = (Severity.CRITICAL if risk > 0.8
                    else Severity.HIGH if risk > 0.6
                    else Severity.MEDIUM)
        return [Detection(
            host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
            detector="ml:isoforest", category="anomaly",
            severity=severity, risk_score=round(risk, 4),
            model_version=self.model_version,
            details={"decision_function": round(raw, 4),
                     "features": dict(zip(Features.vector_names(), f.to_vector()))},
        )]
