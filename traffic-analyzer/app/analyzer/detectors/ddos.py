import logging

from app.models import Alert, AnalyzerSettings
from app.analyzer.base import BaseDetector
from app.analyzer.registry import detector_registry
from app.clickhouse.queries import get_ddos_candidates

logger = logging.getLogger("analyzer.ddos")


@detector_registry.register
class DDoSDetector(BaseDetector):

    @property
    def name(self) -> str:
        return "ddos"

    def is_enabled(self, settings: AnalyzerSettings) -> bool:
        return settings.enable_ddos_detect

    def detect(self, settings: AnalyzerSettings) -> list[Alert]:
        candidates = get_ddos_candidates(settings.window_minutes)
        alerts = []

        for c in candidates:
            pps = c["pps"]
            bps = c["bps"]
            is_pps = pps >= settings.ddos_pps_threshold
            is_bps = bps >= settings.ddos_bps_threshold

            if not (is_pps or is_bps):
                continue

            reasons = []
            if is_pps:
                reasons.append(f"PPS={pps:.0f}")
            if is_bps:
                reasons.append(f"BPS={bps:.0f}")

            alerts.append(Alert(
                host_id=c["host_id"],
                alert_type="ddos",
                severity="critical",
                title=f"Possible DDoS on {c['dst_ip']}",
                description=(
                    f"High rate to {c['dst_ip']}: {', '.join(reasons)}. "
                    f"Sources: {c['unique_sources']}, "
                    f"Total: {c['total_packets']} pkts"
                ),
                dst_ip=c["dst_ip"],
                details_json={
                    "pps": float(pps),
                    "bps": float(bps),
                    "unique_sources": c["unique_sources"],
                    "total_packets": c["total_packets"],
                },
            ))

        logger.info("DDoS: %d detections", len(alerts))
        return alerts
