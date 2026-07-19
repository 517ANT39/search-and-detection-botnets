"""Юнит-тесты оконной логики на event-time."""
from analyzer.windowing import TumblingWindower, SessionWindower, WindowManager


def _add(w, host, ts, port=80, ip=1, plen=100, proto=6):
    return w.add(host, ts, ip, port, plen, proto)


def test_tumbling_bucketing():
    w = TumblingWindower(size_sec=60)
    _add(w, "h1", 10)
    _add(w, "h1", 59)
    _add(w, "h1", 61)   # следующее окно
    # watermark за пределом первого окна (end=60)
    closed = w.pop_closed(watermark=60)
    assert len(closed) == 1
    assert closed[0].packets == 2
    assert closed[0].window_start == 0.0
    assert closed[0].window_end == 60.0


def test_tumbling_not_closed_before_watermark():
    w = TumblingWindower(size_sec=60)
    _add(w, "h1", 10)
    assert w.pop_closed(watermark=30) == []   # окно ещё не закрыто


def test_session_timeout_splits():
    w = SessionWindower(timeout_sec=30)
    _add(w, "h1", 100)
    _add(w, "h1", 120)               # в той же сессии
    closed = _add(w, "h1", 200)      # разрыв > timeout → закрывает прошлую
    assert len(closed) == 1
    assert closed[0].packets == 2


def test_session_expiry_by_watermark():
    w = SessionWindower(timeout_sec=30)
    _add(w, "h1", 100)
    expired = w.pop_expired(watermark=200)
    assert len(expired) == 1
    assert expired[0].packets == 1


def test_window_manager_watermark_and_uniques():
    m = WindowManager(tumbling_sec=60, sliding_sec=120, sliding_step_sec=60,
                      session_timeout_sec=30, watermark_sec=10)
    m.add_event("h1", 10, dst_ip=1, dst_port=80, pkt_len=100, protocol=6)
    m.add_event("h1", 20, dst_ip=2, dst_port=443, pkt_len=200, protocol=6)
    # продвигаем время далеко вперёд → окна первого бакета закрываются
    closed = m.add_event("h1", 200, dst_ip=3, dst_port=22, pkt_len=50, protocol=6)
    tumbling = [f for f in closed if f.window_type == "tumbling"]
    assert tumbling, "первое tumbling-окно должно закрыться"
    first = tumbling[0]
    assert first.uniq_dst_ip == 2
    assert first.uniq_dst_port == 2
