import aiochclient
import aiohttp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional

from .config import (
    CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_DB,
    CLICKHOUSE_USER, CLICKHOUSE_PASSWORD,
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
    POSTGRES_PASSWORD, POSTGRES_DB,
)
from .schemas import Base


# =====================================================================
#  ClickHouse
# =====================================================================

class ClickHouseClient:
    def __init__(self):
        self.client = None
        self.session = None

    async def connect(self):
        self.session = aiohttp.ClientSession()
        self.client = aiochclient.ChClient(
            self.session,
            url=f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}",
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DB,
        )

    async def close(self):
        if self.session:
            await self.session.close()

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _where(time_col: str,
               minutes: Optional[int],
               start_time: Optional[str],
               end_time: Optional[str],
               extra: Optional[list] = None) -> str:
        conds = []
        if start_time:
            conds.append(f"{time_col} >= '{start_time}'")
        if end_time:
            conds.append(f"{time_col} <= '{end_time}'")
        if not start_time and not end_time:
            conds.append(f"{time_col} >= now() - INTERVAL {minutes or 60} MINUTE")
        if extra:
            conds.extend(extra)
        return " AND ".join(conds) if conds else "1=1"

    # ------------------------------------------------------------------
    #  TRAFFIC
    # ------------------------------------------------------------------

    async def fetch_traffic_timeline(self,
                                     minutes: int = 60,
                                     start_time: Optional[str] = None,
                                     end_time: Optional[str] = None,
                                     src_ip: Optional[str] = None,
                                     dst_ip: Optional[str] = None,
                                     protocol: Optional[int] = None,
                                     direction: Optional[int] = None,
                                     host_ip: Optional[str] = None):
        extra = []
        if src_ip:      extra.append(f"src_ip = '{src_ip}'")
        if dst_ip:      extra.append(f"dst_ip = '{dst_ip}'")
        if protocol is not None: extra.append(f"protocol = {protocol}")
        if direction is not None: extra.append(f"direction = {direction}")
        if host_ip:     extra.append(f"(src_ip = '{host_ip}' OR dst_ip = '{host_ip}')")

        where = self._where("window_start", minutes, start_time, end_time, extra)

        query = f"""
            SELECT
                toStartOfMinute(window_start) AS minute,
                sum(packet_count) AS packets,
                sum(byte_sum)     AS bytes
            FROM traffic_stats
            WHERE {where}
            GROUP BY minute
            ORDER BY minute
        """
        return await self.client.fetch(query)

    async def fetch_traffic_by_protocol(self, minutes: int = 60):
        query = f"""
            SELECT protocol,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_stats_by_protocol
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY protocol
            ORDER BY packets DESC
        """
        return await self.client.fetch(query)

    async def fetch_traffic_by_port(self, minutes: int = 60, port_type: str = "dst"):
        query = f"""
            SELECT port,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_stats_by_port
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
              AND port_type = '{port_type}'
            GROUP BY port
            ORDER BY packets DESC
            LIMIT 20
        """
        return await self.client.fetch(query)

    async def fetch_traffic_by_direction(self, minutes: int = 60):
        query = f"""
            SELECT direction,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_stats_by_direction
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY direction
        """
        return await self.client.fetch(query)

    async def fetch_traffic_by_subnet(self, minutes: int = 60, limit: int = 30):
        query = f"""
            SELECT src_subnet, dst_subnet,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_stats_by_subnet
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY src_subnet, dst_subnet
            ORDER BY packets DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    async def fetch_topology(self, minutes: int = 60,
                             min_packets: int = 10,
                             limit: int = 200):
        query = f"""
            SELECT src_ip, dst_ip, protocol,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_stats_by_pair
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY src_ip, dst_ip, protocol
            HAVING packets >= {min_packets}
            ORDER BY packets DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    async def fetch_top_sources(self, minutes: int = 60, limit: int = 20):
        query = f"""
            SELECT src_ip,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_top_sources
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY src_ip
            ORDER BY packets DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    async def fetch_top_targets(self, minutes: int = 60, limit: int = 20):
        query = f"""
            SELECT dst_ip,
                   sum(packet_count) AS packets,
                   sum(byte_sum)     AS bytes
            FROM traffic_top_targets
            WHERE window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY dst_ip
            ORDER BY packets DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    # ------------------------------------------------------------------
    #  HOSTS — статус выводится из traffic_stats_by_host
    # ------------------------------------------------------------------

    async def fetch_hosts(self):
        """Список зарегистрированных хостов."""
        query = """
            SELECT host_id, hostname, os, arch, kernel_version,
                   interfaces, boot_time_sec, register_ts
            FROM hosts_info FINAL
            ORDER BY host_id
        """
        return await self.client.fetch(query)

    async def fetch_host_status(self):
        """
        Статус хостов, вычисленный из traffic_stats_by_host.
        - last_seen   = max(window_start) для host_ip
        - packets_1m  = сумма пакетов за последнюю минуту с данными
        - bytes_1m    = аналогично
        - is_offline  = 1, если последняя активность старше 3 минут
        """
        query = """
            SELECT
                h.host_id,
                h.hostname,
                h.os,
                h.arch,
                h.kernel_version,
                h.interfaces,
                h.boot_time_sec,
                h.register_ts,
                s.last_seen,
                s.packets_1m,
                s.bytes_1m,
                if(s.last_seen IS NULL
                   OR now() - s.last_seen > INTERVAL 3 MINUTE, 1, 0) AS is_offline
            FROM hosts_info AS h FINAL
            LEFT JOIN (
                SELECT
                    host_ip AS host_id,
                    max(window_start) AS last_seen,
                    sumIf(packet_count, window_start >= now() - INTERVAL 1 MINUTE) AS packets_1m,
                    sumIf(byte_sum,     window_start >= now() - INTERVAL 1 MINUTE) AS bytes_1m
                FROM traffic_stats_by_host
                WHERE window_start >= now() - INTERVAL 1 HOUR
                GROUP BY host_ip
            ) AS s ON h.host_id = s.host_id
            ORDER BY h.host_id
        """
        return await self.client.fetch(query)

    async def fetch_host_traffic(self, host_ip: str, minutes: int = 60):
        query = f"""
            SELECT
                toStartOfMinute(window_start) AS minute,
                sumIf(packet_count, role='src') AS packets_sent,
                sumIf(byte_sum,     role='src') AS bytes_sent,
                sumIf(packet_count, role='dst') AS packets_recv,
                sumIf(byte_sum,     role='dst') AS bytes_recv
            FROM traffic_stats_by_host
            WHERE host_ip = '{host_ip}'
              AND window_start >= now() - INTERVAL {minutes} MINUTE
            GROUP BY minute
            ORDER BY minute
        """
        return await self.client.fetch(query)

    # ------------------------------------------------------------------
    #  ALERTS
    # ------------------------------------------------------------------

    async def fetch_alerts(self,
                           limit: int = 200,
                           minutes: Optional[int] = None,
                           start_time: Optional[str] = None,
                           end_time: Optional[str] = None,
                           severity: Optional[str] = None,
                           detector: Optional[str] = None,
                           view: Optional[str] = None,
                           src_ip: Optional[str] = None,
                           dst_ip: Optional[str] = None,
                           protocol: Optional[int] = None):
        extra = []
        if severity: extra.append(f"severity = '{severity}'")
        if detector: extra.append(f"detector = '{detector}'")
        if view:     extra.append(f"view = '{view}'")
        if src_ip:   extra.append(f"src_ip = '{src_ip}'")
        if dst_ip:   extra.append(f"dst_ip = '{dst_ip}'")
        if protocol is not None: extra.append(f"protocol = {protocol}")

        where = self._where("timestamp", minutes, start_time, end_time, extra)

        query = f"""
            SELECT
                timestamp, detector, view,
                src_ip, src_port, dst_ip, dst_port, protocol, direction,
                packet_count, byte_sum, active_minutes, avg_per_min,
                baseline_value, baseline_stddev, z_score,
                anomaly_type, severity, host_id
            FROM alerts
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    async def fetch_alert_timeline(self, minutes: int = 60):
        query = f"""
            SELECT
                toStartOfMinute(timestamp) AS minute,
                count() AS total,
                countIf(severity = 'critical') AS critical,
                countIf(severity = 'warning')  AS warning,
                countIf(severity = 'info')     AS info
            FROM alerts
            WHERE timestamp >= now() - INTERVAL {minutes} MINUTE
            GROUP BY minute
            ORDER BY minute
        """
        return await self.client.fetch(query)

    async def fetch_alert_by_view(self, minutes: int = 60):
        query = f"""
            SELECT view, count() AS count
            FROM alerts
            WHERE timestamp >= now() - INTERVAL {minutes} MINUTE
            GROUP BY view
            ORDER BY count DESC
        """
        return await self.client.fetch(query)

    async def fetch_alert_by_severity(self, minutes: int = 60):
        query = f"""
            SELECT severity, count() AS count
            FROM alerts
            WHERE timestamp >= now() - INTERVAL {minutes} MINUTE
            GROUP BY severity
        """
        return await self.client.fetch(query)

    async def fetch_top_alert_targets(self, minutes: int = 60, limit: int = 10):
        query = f"""
            SELECT dst_ip, count() AS count, max(z_score) AS max_z
            FROM alerts
            WHERE timestamp >= now() - INTERVAL {minutes} MINUTE
              AND dst_ip != ''
            GROUP BY dst_ip
            ORDER BY count DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    async def fetch_top_alert_sources(self, minutes: int = 60, limit: int = 10):
        query = f"""
            SELECT src_ip, count() AS count, max(z_score) AS max_z
            FROM alerts
            WHERE timestamp >= now() - INTERVAL {minutes} MINUTE
              AND src_ip != ''
            GROUP BY src_ip
            ORDER BY count DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)


# Глобальный ClickHouse-клиент
db = ClickHouseClient()


# =====================================================================
#  PostgreSQL
# =====================================================================

POSTGRES_DSN = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
postgres_engine = create_engine(POSTGRES_DSN, pool_pre_ping=True)
PostgresSessionLocal = sessionmaker(autocommit=False, autoflush=False,
                                    bind=postgres_engine)


def get_postgres_session():
    db_ = PostgresSessionLocal()
    try:
        yield db_
    finally:
        db_.close()


def init_postgres():
    Base.metadata.create_all(bind=postgres_engine)