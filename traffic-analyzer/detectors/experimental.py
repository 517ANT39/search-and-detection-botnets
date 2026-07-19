"""Экспериментальные ядра (скелеты с корректными сигнатурами).

Реализуют интерфейс Detector, готовы к подключению через реестр для сравнения
ядер в бенчмарке. Обучаются офлайн (fit) на векторах фич из ClickHouse.
"""
from __future__ import annotations

import logging
import os

import joblib
import numpy as np

from analyzer.detectors.base import Detection, Detector, Features, Severity

logger = logging.getLogger(__name__)


class _SklearnUnsupervised(Detector):
    """Общая логика для sklearn-ядер обнаружения аномалий."""

    _estimator_cls = None      # переопределяется в наследнике
    _estimator_kwargs: dict = {}

    def __init__(self, model_path: str, model_version: str = "v1") -> None:
        self.model_path = model_path
        self.model_version = model_version
        self._model = None
        if os.path.exists(model_path):
            try:
                self._model = joblib.load(model_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("%s: load failed: %s", self.name, exc)

    def fit(self, X: list[list[float]]) -> None:  # noqa: N803
        arr = np.asarray(X, dtype=float)
        if arr.size == 0:
            return
        model = self._estimator_cls(**self._estimator_kwargs)  # type: ignore[misc]
        model.fit(arr)
        self._model = model
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        joblib.dump(model, self.model_path)
        logger.info("%s trained on %d samples", self.name, len(X))

    def _predict_anomaly(self, vec: np.ndarray) -> bool:
        return bool(self._model.predict(vec)[0] == -1)  # type: ignore[union-attr]

    def score(self, f: Features) -> list[Detection]:
        if self._model is None:
            return []
        vec = np.asarray([f.to_vector()], dtype=float)
        if not self._predict_anomaly(vec):
            return []
        return [Detection(
            host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
            detector=f"ml:{self.name}", category="anomaly",
            severity=Severity.MEDIUM, risk_score=0.7,
            model_version=self.model_version,
            details={"features": dict(zip(Features.vector_names(), f.to_vector()))},
        )]


class LOFDetector(_SklearnUnsupervised):
    name = "lof"

    def __init__(self, model_path: str, model_version: str = "v1") -> None:
        from sklearn.neighbors import LocalOutlierFactor
        self._estimator_cls = LocalOutlierFactor
        self._estimator_kwargs = {"novelty": True, "n_neighbors": 20}
        super().__init__(model_path, model_version)


class OCSVMDetector(_SklearnUnsupervised):
    name = "ocsvm"

    def __init__(self, model_path: str, model_version: str = "v1") -> None:
        from sklearn.svm import OneClassSVM
        self._estimator_cls = OneClassSVM
        self._estimator_kwargs = {"kernel": "rbf", "gamma": "scale", "nu": 0.02}
        super().__init__(model_path, model_version)


class KMeansDetector(Detector):
    """Кластеризация нормы; аномалия = большое расстояние до ближайшего центроида."""

    name = "kmeans"

    def __init__(self, model_path: str, model_version: str = "v1",
                 n_clusters: int = 8, dist_percentile: float = 99.0) -> None:
        self.model_path = model_path
        self.model_version = model_version
        self.n_clusters = n_clusters
        self.dist_percentile = dist_percentile
        self._model = None
        self._threshold = float("inf")
        if os.path.exists(model_path):
            try:
                blob = joblib.load(model_path)
                self._model, self._threshold = blob["model"], blob["threshold"]
            except Exception as exc:  # noqa: BLE001
                logger.error("kmeans: load failed: %s", exc)

    def fit(self, X: list[list[float]]) -> None:  # noqa: N803
        from sklearn.cluster import KMeans

        arr = np.asarray(X, dtype=float)
        if arr.size == 0:
            return
        model = KMeans(n_clusters=min(self.n_clusters, len(arr)),
                       random_state=42, n_init="auto")
        model.fit(arr)
        dists = np.min(model.transform(arr), axis=1)
        self._threshold = float(np.percentile(dists, self.dist_percentile))
        self._model = model
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        joblib.dump({"model": model, "threshold": self._threshold}, self.model_path)
        logger.info("kmeans trained on %d samples, threshold=%.4f",
                    len(X), self._threshold)

    def score(self, f: Features) -> list[Detection]:
        if self._model is None:
            return []
        vec = np.asarray([f.to_vector()], dtype=float)
        dist = float(np.min(self._model.transform(vec)))
        if dist <= self._threshold:
            return []
        risk = float(np.clip(dist / (self._threshold * 2), 0.0, 1.0))
        return [Detection(
            host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
            detector="ml:kmeans", category="anomaly",
            severity=Severity.HIGH if risk > 0.6 else Severity.MEDIUM,
            risk_score=round(risk, 4), model_version=self.model_version,
            details={"distance": round(dist, 4), "threshold": round(self._threshold, 4)},
        )]


class MLPDetector(Detector):
    """Простая нейросеть (sklearn MLP) как autoencoder-подобный детектор ошибки.

    Обучается предсказывать вход по входу (identity через bottleneck); большая
    ошибка реконструкции → аномалия. Экспериментальное ядро.
    """

    name = "mlp"

    def __init__(self, model_path: str, model_version: str = "v1",
                 err_percentile: float = 99.0) -> None:
        self.model_path = model_path
        self.model_version = model_version
        self.err_percentile = err_percentile
        self._model = None
        self._scaler = None
        self._threshold = float("inf")
        if os.path.exists(model_path):
            try:
                blob = joblib.load(model_path)
                self._model = blob["model"]
                self._scaler = blob["scaler"]
                self._threshold = blob["threshold"]
            except Exception as exc:  # noqa: BLE001
                logger.error("mlp: load failed: %s", exc)

    def fit(self, X: list[list[float]]) -> None:  # noqa: N803
        from sklearn.neural_network import MLPRegressor
        from sklearn.preprocessing import StandardScaler

        arr = np.asarray(X, dtype=float)
        if arr.size == 0:
            return
        scaler = StandardScaler().fit(arr)
        Xs = scaler.transform(arr)
        model = MLPRegressor(hidden_layer_sizes=(16, 4, 16), max_iter=300,
                             random_state=42)
        model.fit(Xs, Xs)  # autoencoder: вход -> вход
        recon = model.predict(Xs)
        errors = np.mean((Xs - recon) ** 2, axis=1)
        self._threshold = float(np.percentile(errors, self.err_percentile))
        self._model, self._scaler = model, scaler
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        joblib.dump({"model": model, "scaler": scaler,
                     "threshold": self._threshold}, self.model_path)
        logger.info("mlp trained on %d samples, err_threshold=%.4f",
                    len(X), self._threshold)

    def score(self, f: Features) -> list[Detection]:
        if self._model is None or self._scaler is None:
            return []
        vec = self._scaler.transform([f.to_vector()])
        recon = self._model.predict(vec)
        err = float(np.mean((vec - recon) ** 2))
        if err <= self._threshold:
            return []
        risk = float(np.clip(err / (self._threshold * 2), 0.0, 1.0))
        return [Detection(
            host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
            detector="nn:mlp", category="anomaly",
            severity=Severity.HIGH if risk > 0.6 else Severity.MEDIUM,
            risk_score=round(risk, 4), model_version=self.model_version,
            details={"recon_error": round(err, 6),
                     "threshold": round(self._threshold, 6)},
        )]
