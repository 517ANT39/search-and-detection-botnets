import logging
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.models import Alert, AnalyzerSettings
from app.analyzer.base import BaseDetector
from app.analyzer.registry import detector_registry
from app.analyzer.features import extract_features, FEATURE_COLUMNS
from app.clickhouse.queries import get_packets_for_analysis

logger = logging.getLogger("analyzer.isolation_forest")


@detector_registry.register
class IsolationForestDetector(BaseDetector):

    @property
    def name(self) -> str:
        return "isolation_forest"

    def is_enabled(self, settings: AnalyzerSettings) -> bool:
        return settings.enable_isolation_forest

    def detect(self, settings: AnalyzerSettings) -> list[Alert]:
        df = get_packets_for_analysis(settings.window_minutes)
        if df.empty or len(df) < settings.min_samples:
            logger.info("Not enough samples (%d)", len(df))
            return []

        features_df = extract_features(df)
        if features_df.empty:
            return []

        X = features_df[FEATURE_COLUMNS].values
        X_scaled = StandardScaler().fit_transform(X)

        model = IsolationForest(
            contamination=settings.contamination,
            n_estimators=settings.n_estimators,
            random_state=42,
            n_jobs=-1,
        )
        preds = model.fit_predict(X_scaled)
        scores = model.decision_function(X_scaled)

        alerts = []
        for idx in range(len(features_df)):
            if preds[idx] != -1:
                continue

            row = features_df.iloc[idx]
            score = abs(scores[idx])

            if score > 0.3:
                severity = "critical"
            elif score > 0.2:
                severity = "high"
            elif score > 0.1:
                severity = "medium"
            else:
                severity = "low"

            alerts.append(Alert(
                host_id=row["host_id"],
                alert_type="anomaly",
                severity=severity,
                title=f"Anomalous traffic from {row['src_ip']}",
                description=(
                    f"IsolationForest score={scores[idx]:.4f}, "
                    f"packets={int(row['total_packets'])}, "
                    f"bytes={int(row['total_bytes'])}, "
                    f"unique_dst_ports={int(row['unique_dst_ports'])}, "
                    f"pps={row['pps']:.1f}"
                ),
                src_ip=str(row["src_ip"]),
                details_json={
                    "score": float(scores[idx]),
                    "total_packets": int(row["total_packets"]),
                    "total_bytes": int(row["total_bytes"]),
                    "pps": float(row["pps"]),
                },
            ))

        logger.info("IsolationForest: %d anomalies / %d flows", len(alerts), len(features_df))
        return alerts
