"""Сверхлёгкое статистическое ядро: EWMA + z-score/MAD по хосту."""
from __future__ import annotations

import math
from collections import defaultdict

from analyzer.detectors.base import Detection, Detector, Features, Severity


class _RunningStat:
    """Онлайн EWMA-среднее и дисперсия для одной метрики."""

    def __init__(self, alpha: float = 0.2) -> None:
        self.alpha = alpha
        self.mean: float | None = None
        self.var = 0.0

    def update(self, x: float) -> float:
        """Возвращает z-score относительно текущего профиля, затем обновляет его."""
        if self.mean is None:
            self.mean = x
            return 0.0
        std = math.sqrt(self.var) if self.var > 0 else 0.0
        z = (x - self.mean) / std if std > 1e-9 else 0.0
        # обновление EWMA
        diff = x - self.mean
        self.mean += self.alpha * diff
        self.var = (1 - self.alpha) * (self.var + self.alpha * diff * diff)
        return z


class ZScoreDetector(Detector):
    """Отклонение метрик хоста от собственного EWMA-профиля."""

    name = "zscore"
    METRICS = ("pps", "bps", "uniq_dst_ip", "uniq_dst_port")

    def __init__(self, z_threshold: float = 4.0, alpha: float = 0.2) -> None:
        self.z_threshold = z_threshold
        # host_id -> metric -> RunningStat
        self._stats: dict[str, dict[str, _RunningStat]] = defaultdict(
            lambda: {m: _RunningStat(alpha) for m in self.METRICS}
        )

    def score(self, f: Features) -> list[Detection]:
        stats = self._stats[f.host_id]
        values = {"pps": f.pps, "bps": f.bps,
                  "uniq_dst_ip": float(f.uniq_dst_ip),
                  "uniq_dst_port": float(f.uniq_dst_port)}

        anomalies = {}
        for metric, val in values.items():
            z = stats[metric].update(val)
            if abs(z) >= self.z_threshold:
                anomalies[metric] = round(z, 2)

        if not anomalies:
            return []

        max_z = max(abs(v) for v in anomalies.values())
        risk = min(1.0, max_z / (self.z_threshold * 2))
        return [Detection(
            host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
            detector="ml:zscore", category="anomaly",
            severity=Severity.HIGH if risk > 0.6 else Severity.MEDIUM,
            risk_score=round(risk, 4),
            details={"z_scores": anomalies, "threshold": self.z_threshold},
        )]
