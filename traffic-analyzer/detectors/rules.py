"""Rule-based детектор: пороги, port/host-scan, beaconing."""
from __future__ import annotations

from analyzer.config import Thresholds
from analyzer.detectors.base import Detection, Detector, Features, Severity


class RuleDetector(Detector):
    """Пороговые и эвристические правила. Всегда активен."""

    name = "rule"

    def __init__(self, thresholds: Thresholds) -> None:
        self.t = thresholds

    def score(self, f: Features) -> list[Detection]:
        out: list[Detection] = []

        # ── DoS / объёмная аномалия ──
        if f.pps > self.t.pps or f.bps > self.t.bps:
            score = min(1.0, max(f.pps / self.t.pps, f.bps / self.t.bps) / 3.0)
            out.append(Detection(
                host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
                detector="rule:volume", category="dos",
                severity=Severity.HIGH if score > 0.5 else Severity.MEDIUM,
                risk_score=round(score, 4),
                details={"pps": f.pps, "bps": f.bps,
                         "pps_thr": self.t.pps, "bps_thr": self.t.bps},
            ))

        # ── Port-scan: всплеск уникальных dst_port ──
        if f.uniq_dst_port >= self.t.uniq_dst_port_scan:
            score = min(1.0, f.uniq_dst_port / (self.t.uniq_dst_port_scan * 3))
            out.append(Detection(
                host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
                detector="rule:port_scan", category="scan",
                severity=Severity.HIGH if score > 0.6 else Severity.MEDIUM,
                risk_score=round(score, 4),
                details={"uniq_dst_port": f.uniq_dst_port,
                         "threshold": self.t.uniq_dst_port_scan},
            ))

        # ── Host-scan: всплеск уникальных dst_ip ──
        if f.uniq_dst_ip >= self.t.uniq_dst_ip_scan:
            score = min(1.0, f.uniq_dst_ip / (self.t.uniq_dst_ip_scan * 3))
            out.append(Detection(
                host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
                detector="rule:host_scan", category="scan",
                severity=Severity.HIGH if score > 0.6 else Severity.MEDIUM,
                risk_score=round(score, 4),
                details={"uniq_dst_ip": f.uniq_dst_ip,
                         "threshold": self.t.uniq_dst_ip_scan},
            ))

        # ── Beaconing / C2: регулярные равноинтервальные соединения ──
        # (низкий std интервалов при достаточном числе соединений; только session-окна)
        if (f.window_type == "session"
                and f.packets >= self.t.beacon_min_conns
                and f.conn_interval_avg > 0
                and f.conn_interval_std <= self.t.beacon_std_max):
            # чем регулярнее (меньше std), тем выше риск
            regularity = 1.0 - min(1.0, f.conn_interval_std / max(self.t.beacon_std_max, 1e-6))
            score = round(0.5 + 0.5 * regularity, 4)
            out.append(Detection(
                host_id=f.host_id, window_start=f.window_start, window_end=f.window_end,
                detector="rule:beaconing", category="c2",
                severity=Severity.CRITICAL if score > 0.8 else Severity.HIGH,
                risk_score=score,
                details={"conn_interval_avg": f.conn_interval_avg,
                         "conn_interval_std": f.conn_interval_std,
                         "connections": f.packets},
            ))

        return out
