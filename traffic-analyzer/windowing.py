"""Оконная агрегация на event-time: tumbling / sliding / session + watermark."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from analyzer.detectors.base import Features


@dataclass
class _Accumulator:
    """Накопитель метрик одного окна одного хоста."""
    host_id: str
    window_type: str
    start: float
    end: float
    packets: int = 0
    total_bytes: int = 0
    dst_ips: set[int] = field(default_factory=set)
    dst_ports: set[int] = field(default_factory=set)
    proto_tcp: int = 0
    proto_udp: int = 0
    proto_other: int = 0
    last_ts: float | None = None
    intervals: list[float] = field(default_factory=list)

    def add(self, ts: float, dst_ip: int, dst_port: int,
            pkt_len: int, protocol: int) -> None:
        self.packets += 1
        self.total_bytes += pkt_len
        self.dst_ips.add(dst_ip)
        self.dst_ports.add(dst_port)
        if protocol == 6:       # TCP
            self.proto_tcp += 1
        elif protocol == 17:    # UDP
            self.proto_udp += 1
        else:
            self.proto_other += 1
        if self.last_ts is not None:
            self.intervals.append(ts - self.last_ts)
        self.last_ts = ts

    def to_features(self) -> Features:
        duration = max(self.end - self.start, 1e-6)
        if self.intervals:
            avg = sum(self.intervals) / len(self.intervals)
            var = sum((x - avg) ** 2 for x in self.intervals) / len(self.intervals)
            std = math.sqrt(var)
        else:
            avg = std = 0.0
        return Features(
            host_id=self.host_id,
            window_start=self.start,
            window_end=self.end,
            window_type=self.window_type,
            packets=self.packets,
            bytes=self.total_bytes,
            pps=self.packets / duration,
            bps=self.total_bytes * 8 / duration,
            uniq_dst_ip=len(self.dst_ips),
            uniq_dst_port=len(self.dst_ports),
            proto_tcp=self.proto_tcp,
            proto_udp=self.proto_udp,
            proto_other=self.proto_other,
            conn_interval_avg=avg,
            conn_interval_std=std,
        )


class TumblingWindower:
    """Непересекающиеся окна фиксированного размера на event-time."""

    def __init__(self, size_sec: int) -> None:
        self.size = size_sec
        self._acc: dict[tuple[str, int], _Accumulator] = {}

    def _bucket(self, ts: float) -> int:
        return int(ts // self.size)

    def add(self, host_id: str, ts: float, dst_ip: int, dst_port: int,
            pkt_len: int, protocol: int) -> None:
        b = self._bucket(ts)
        key = (host_id, b)
        acc = self._acc.get(key)
        if acc is None:
            start = b * self.size
            acc = _Accumulator(host_id, "tumbling", float(start),
                               float(start + self.size))
            self._acc[key] = acc
        acc.add(ts, dst_ip, dst_port, pkt_len, protocol)

    def pop_closed(self, watermark: float) -> list[Features]:
        """Возвращает окна, полностью прошедшие watermark, и удаляет их."""
        closed: list[Features] = []
        for key in list(self._acc.keys()):
            acc = self._acc[key]
            if acc.end <= watermark:
                closed.append(acc.to_features())
                del self._acc[key]
        return closed

    def flush_all(self) -> list[Features]:
        out = [a.to_features() for a in self._acc.values()]
        self._acc.clear()
        return out


class SlidingWindower:
    """Скользящие окна: size с шагом step. Каждое событие попадает в несколько окон."""

    def __init__(self, size_sec: int, step_sec: int) -> None:
        self.size = size_sec
        self.step = step_sec
        self._acc: dict[tuple[str, int], _Accumulator] = {}

    def _slots(self, ts: float) -> list[int]:
        """Индексы шаговых слотов, чьи окна [slot*step, slot*step+size) покрывают ts."""
        last = int(ts // self.step)
        first = int((ts - self.size) // self.step) + 1
        return list(range(max(first, 0), last + 1))

    def add(self, host_id: str, ts: float, dst_ip: int, dst_port: int,
            pkt_len: int, protocol: int) -> None:
        for slot in self._slots(ts):
            key = (host_id, slot)
            acc = self._acc.get(key)
            if acc is None:
                start = slot * self.step
                acc = _Accumulator(host_id, "sliding", float(start),
                                   float(start + self.size))
                self._acc[key] = acc
            acc.add(ts, dst_ip, dst_port, pkt_len, protocol)

    def pop_closed(self, watermark: float) -> list[Features]:
        closed: list[Features] = []
        for key in list(self._acc.keys()):
            acc = self._acc[key]
            if acc.end <= watermark:
                closed.append(acc.to_features())
                del self._acc[key]
        return closed

    def flush_all(self) -> list[Features]:
        out = [a.to_features() for a in self._acc.values()]
        self._acc.clear()
        return out


class SessionWindower:
    """Session-окна: активность хоста с таймаутом простоя."""

    def __init__(self, timeout_sec: int) -> None:
        self.timeout = timeout_sec
        self._open: dict[str, _Accumulator] = {}

    def add(self, host_id: str, ts: float, dst_ip: int, dst_port: int,
            pkt_len: int, protocol: int) -> list[Features]:
        """Возвращает закрытые (по таймауту) сессии, если событие их разорвало."""
        closed: list[Features] = []
        acc = self._open.get(host_id)
        if acc is not None and acc.last_ts is not None and \
                ts - acc.last_ts > self.timeout:
            acc.end = acc.last_ts
            closed.append(acc.to_features())
            acc = None
        if acc is None:
            acc = _Accumulator(host_id, "session", ts, ts)
            self._open[host_id] = acc
        acc.end = ts
        acc.add(ts, dst_ip, dst_port, pkt_len, protocol)
        return closed

    def pop_expired(self, watermark: float) -> list[Features]:
        """Закрывает сессии, чей простой превысил таймаут относительно watermark."""
        closed: list[Features] = []
        for host_id in list(self._open.keys()):
            acc = self._open[host_id]
            if acc.last_ts is not None and watermark - acc.last_ts > self.timeout:
                acc.end = acc.last_ts
                closed.append(acc.to_features())
                del self._open[host_id]
        return closed

    def flush_all(self) -> list[Features]:
        out = []
        for acc in self._open.values():
            if acc.last_ts is not None:
                acc.end = acc.last_ts
            out.append(acc.to_features())
        self._open.clear()
        return out


class WindowManager:
    """Оркестратор всех окон + отслеживание watermark по event-time."""

    def __init__(self, tumbling_sec: int, sliding_sec: int, sliding_step_sec: int,
                 session_timeout_sec: int, watermark_sec: int) -> None:
        self.tumbling = TumblingWindower(tumbling_sec)
        self.sliding = SlidingWindower(sliding_sec, sliding_step_sec)
        self.session = SessionWindower(session_timeout_sec)
        self.watermark_lag = watermark_sec
        self._max_ts = 0.0
        self.late_events = 0

    @property
    def watermark(self) -> float:
        return self._max_ts - self.watermark_lag

    def add_event(self, host_id: str, ts: float, dst_ip: int, dst_port: int,
                  pkt_len: int, protocol: int) -> list[Features]:
        """Добавляет событие, возвращает все окна, закрывшиеся в результате."""
        # поздние события: за watermark — считаем, но помечаем
        if ts < self.watermark:
            self.late_events += 1

        self._max_ts = max(self._max_ts, ts)

        self.tumbling.add(host_id, ts, dst_ip, dst_port, pkt_len, protocol)
        self.sliding.add(host_id, ts, dst_ip, dst_port, pkt_len, protocol)
        closed = self.session.add(host_id, ts, dst_ip, dst_port, pkt_len, protocol)

        wm = self.watermark
        closed.extend(self.tumbling.pop_closed(wm))
        closed.extend(self.sliding.pop_closed(wm))
        closed.extend(self.session.pop_expired(wm))
        return closed

    def flush_all(self) -> list[Features]:
        """Принудительно закрывает все окна (при shutdown)."""
        out: list[Features] = []
        out.extend(self.tumbling.flush_all())
        out.extend(self.sliding.flush_all())
        out.extend(self.session.flush_all())
        return out
