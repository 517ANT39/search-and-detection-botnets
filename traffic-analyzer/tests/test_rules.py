"""Юнит-тесты RuleDetector."""
from analyzer.config import Thresholds
from analyzer.detectors.base import Features, Severity
from analyzer.detectors.rules import RuleDetector


def _features(**kw) -> Features:
    base = dict(
        host_id="h1", window_start=0.0, window_end=60.0, window_type="tumbling",
        packets=10, bytes=1000, pps=1.0, bps=1000.0,
        uniq_dst_ip=1, uniq_dst_port=1,
        proto_tcp=10, proto_udp=0, proto_other=0,
        conn_interval_avg=0.0, conn_interval_std=0.0,
    )
    base.update(kw)
    return Features(**base)


def test_port_scan_detected():
    det = RuleDetector(Thresholds(uniq_dst_port_scan=100))
    res = det.score(_features(uniq_dst_port=150))
    assert any(d.detector == "rule:port_scan" for d in res)


def test_host_scan_detected():
    det = RuleDetector(Thresholds(uniq_dst_ip_scan=100))
    res = det.score(_features(uniq_dst_ip=200))
    assert any(d.detector == "rule:host_scan" for d in res)


def test_volume_dos_detected():
    det = RuleDetector(Thresholds(pps=1000.0))
    res = det.score(_features(pps=5000.0))
    assert any(d.detector == "rule:volume" and d.category == "dos" for d in res)


def test_beaconing_on_session_only():
    t = Thresholds(beacon_std_max=0.5, beacon_min_conns=5)
    det = RuleDetector(t)
    # tumbling — beaconing НЕ должен срабатывать
    res_tumbling = det.score(_features(
        window_type="tumbling", packets=10,
        conn_interval_avg=60.0, conn_interval_std=0.1))
    assert not any(d.detector == "rule:beaconing" for d in res_tumbling)
    # session с регулярными интервалами — срабатывает
    res_session = det.score(_features(
        window_type="session", packets=10,
        conn_interval_avg=60.0, conn_interval_std=0.1))
    beacon = [d for d in res_session if d.detector == "rule:beaconing"]
    assert beacon and beacon[0].severity >= Severity.HIGH


def test_no_false_positive_on_normal_traffic():
    det = RuleDetector(Thresholds())
    assert det.score(_features()) == []
