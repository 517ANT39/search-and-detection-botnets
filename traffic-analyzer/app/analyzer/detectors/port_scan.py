import logging

from app.models import Alert, AnalyzerSettings
from app.analyzer.base import BaseDetector
from app.analyzer.registry import detector_registry
from app.clickhouse.queries import get_port_scan_candidates

logger = logging.getLogger("analyzer.port_scan")


@detector_registry.register
class PortScanDetector(BaseDetector):

    @property
    def name(self) -> str:
        return "port_scan"

    def is_enabled(self, settings: AnalyzerSettings) -> bool:
        return settings.enable_port_scan_detect

    def detect(self, settings: AnalyzerSettings) -> list[Alert]:
        candidates = get_port_scan_candidates(
            settings.window_minutes,
            settings.port_scan_threshold,
        )
        alerts = []
        for c in candidates:
            alerts.append(Alert(
                host_id=c["host_id"],
                alert_type="port_scan",
                severity="high",
                title=f"Port scan from {c['src_ip']}",
                description=(
                    f"{c['src_ip']} scanned {c['unique_ports']} unique ports "
                    f"({c['total_packets']} pkts in {settings.window_minutes} min)"
                ),
                src_ip=c["src_ip"],
                details_json={
                    "unique_ports": c["unique_ports"],
                    "total_packets": c["total_packets"],
                    "sample_ports": c.get("sample_ports", [])[:50],
                },
            ))

        logger.info("PortScan: %d detections", len(alerts))
        return alerts
