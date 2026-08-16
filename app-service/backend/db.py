import aiochclient
import aiohttp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import *
from .schemas import Base

# ---------- ClickHouse ----------
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
        await self._create_tables()

    async def _create_tables(self):
        # traffic_stats
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS traffic_stats (
                window_start DateTime,
                src_ip String,
                dst_ip String,
                src_port UInt16,
                dst_port UInt16,
                protocol UInt8,
                direction UInt8,
                packet_count UInt64,
                byte_sum UInt64
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMMDD(window_start)
            ORDER BY (src_ip, dst_ip, src_port, dst_port, protocol, direction, window_start)
        """)
        # hosts_info
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS hosts_info (
                host_id String,
                hostname String,
                os String,
                arch String,
                kernel_version String,
                interfaces String,
                boot_time_sec DateTime,
                register_ts DateTime
            ) ENGINE = ReplacingMergeTree(register_ts)
            ORDER BY host_id
        """)
        # alerts
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                timestamp DateTime,
                src_ip String,
                dst_ip String,
                src_port UInt16,
                dst_port UInt16,
                protocol UInt8,
                direction UInt8,
                packet_count UInt64,
                byte_sum UInt64,
                threshold_count Float64,
                threshold_bytes Float64,
                anomaly_type String,
                host_id String
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMMDD(timestamp)
            ORDER BY (timestamp, src_ip, dst_ip)
        """)
        # traffic_stats_by_host
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS traffic_stats_by_host (
                window_start DateTime,
                host_ip String,
                direction UInt8,
                packet_count UInt64,
                byte_sum UInt64
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMMDD(window_start)
            ORDER BY (host_ip, direction, window_start)
        """)
        # traffic_stats_by_protocol
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS traffic_stats_by_protocol (
                window_start DateTime,
                protocol UInt8,
                packet_count UInt64,
                byte_sum UInt64
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMMDD(window_start)
            ORDER BY (protocol, window_start)
        """)
        # traffic_stats_by_port
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS traffic_stats_by_port (
                window_start DateTime,
                port UInt16,
                packet_count UInt64,
                byte_sum UInt64
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMMDD(window_start)
            ORDER BY (port, window_start)
        """)

    async def insert_host(self, host_data: dict):
        # Используем INSERT ... ON CONFLICT DO NOTHING (для ReplacingMergeTree сработает)
        # Но проще выполнить INSERT, ReplacingMergeTree заменит по host_id при слиянии
        query = """
            INSERT INTO hosts_info (host_id, hostname, os, arch, kernel_version,
                                    interfaces, boot_time_sec, register_ts)
            VALUES
        """
        await self.client.execute(query, [tuple(host_data.values())])

    async def insert_alert(self, alert: dict):
        query = """
            INSERT INTO alerts (timestamp, src_ip, dst_ip, src_port, dst_port,
                                protocol, direction, packet_count, byte_sum,
                                threshold_count, threshold_bytes, anomaly_type, host_id)
            VALUES
        """
        values = (
            alert["timestamp"],
            alert["src_ip"],
            alert["dst_ip"],
            alert["src_port"],
            alert["dst_port"],
            alert["protocol"],
            alert["direction"],
            alert["packet_count"],
            alert["byte_sum"],
            alert["threshold_count"],
            alert["threshold_bytes"],
            alert["anomaly_type"],
            alert.get("host_id", ""),
        )
        await self.client.execute(query, [values])

    # ---------- Методы для извлечения данных с фильтрацией ----------
    async def fetch_traffic_stats_filtered(self, start_time=None, end_time=None,
                                           src_ip=None, dst_ip=None,
                                           protocol=None, direction=None,
                                           host_ip=None):
        conditions = []
        if start_time:
            conditions.append(f"window_start >= '{start_time}'")
        if end_time:
            conditions.append(f"window_start <= '{end_time}'")
        if src_ip:
            conditions.append(f"src_ip = '{src_ip}'")
        if dst_ip:
            conditions.append(f"dst_ip = '{dst_ip}'")
        if protocol is not None:
            conditions.append(f"protocol = {protocol}")
        if direction is not None:
            conditions.append(f"direction = {direction}")
        if host_ip:
            conditions.append(f"(src_ip = '{host_ip}' OR dst_ip = '{host_ip}')")
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT 
                toStartOfMinute(window_start) AS minute,
                sum(packet_count) AS total_packets,
                sum(byte_sum) AS total_bytes
            FROM traffic_stats
            WHERE {where_clause}
            GROUP BY minute
            ORDER BY minute
        """
        return await self.client.fetch(query)

    async def fetch_topology_filtered(self, start_time=None, end_time=None,
                                      src_ip=None, dst_ip=None,
                                      protocol=None, direction=None,
                                      min_packets=10):
        conditions = []
        if start_time:
            conditions.append(f"window_start >= '{start_time}'")
        if end_time:
            conditions.append(f"window_start <= '{end_time}'")
        if src_ip:
            conditions.append(f"src_ip = '{src_ip}'")
        if dst_ip:
            conditions.append(f"dst_ip = '{dst_ip}'")
        if protocol is not None:
            conditions.append(f"protocol = {protocol}")
        if direction is not None:
            conditions.append(f"direction = {direction}")
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT src_ip, dst_ip,
                   sum(packet_count) AS total_packets,
                   sum(byte_sum) AS total_bytes
            FROM traffic_stats
            WHERE {where_clause}
            GROUP BY src_ip, dst_ip
            HAVING total_packets >= {min_packets}
            ORDER BY total_packets DESC
            LIMIT 200
        """
        return await self.client.fetch(query)

    async def fetch_hosts(self):
        # Для ReplacingMergeTree используем FINAL, чтобы получить последние записи
        return await self.client.fetch("SELECT * FROM hosts_info FINAL")

    async def fetch_alerts_filtered(self, start_time=None, end_time=None,
                                    src_ip=None, dst_ip=None,
                                    protocol=None, direction=None,
                                    anomaly_type=None, limit=100):
        conditions = []
        if start_time:
            conditions.append(f"timestamp >= '{start_time}'")
        if end_time:
            conditions.append(f"timestamp <= '{end_time}'")
        if src_ip:
            conditions.append(f"src_ip = '{src_ip}'")
        if dst_ip:
            conditions.append(f"dst_ip = '{dst_ip}'")
        if protocol is not None:
            conditions.append(f"protocol = {protocol}")
        if direction is not None:
            conditions.append(f"direction = {direction}")
        if anomaly_type:
            conditions.append(f"anomaly_type = '{anomaly_type}'")
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT *
            FROM alerts
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit}
        """
        return await self.client.fetch(query)

    async def fetch_host_traffic(self, host_ip: str, start_time=None, end_time=None):
        conditions = [f"(host_ip = '{host_ip}')"]
        if start_time:
            conditions.append(f"window_start >= '{start_time}'")
        if end_time:
            conditions.append(f"window_start <= '{end_time}'")
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT 
                toStartOfMinute(window_start) AS minute,
                sum(packet_count) AS packets,
                sum(byte_sum) AS bytes
            FROM traffic_stats_by_host
            WHERE {where_clause}
            GROUP BY minute
            ORDER BY minute
        """
        return await self.client.fetch(query)

    async def fetch_protocol_stats(self, start_time=None, end_time=None):
        conditions = []
        if start_time:
            conditions.append(f"window_start >= '{start_time}'")
        if end_time:
            conditions.append(f"window_start <= '{end_time}'")
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT protocol,
                   sum(packet_count) AS packets,
                   sum(byte_sum) AS bytes
            FROM traffic_stats_by_protocol
            WHERE {where_clause}
            GROUP BY protocol
        """
        return await self.client.fetch(query)

    async def fetch_port_stats(self, start_time=None, end_time=None):
        conditions = []
        if start_time:
            conditions.append(f"window_start >= '{start_time}'")
        if end_time:
            conditions.append(f"window_start <= '{end_time}'")
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT port,
                   sum(packet_count) AS packets,
                   sum(byte_sum) AS bytes
            FROM traffic_stats_by_port
            WHERE {where_clause}
            GROUP BY port
            ORDER BY packets DESC
            LIMIT 20
        """
        return await self.client.fetch(query)

    async def close(self):
        if self.session:
            await self.session.close()

# ---------- PostgreSQL (SQLAlchemy) ----------
postgres_engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
PostgresSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)

def get_postgres_session():
    db = PostgresSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Создание таблиц в PostgreSQL при импорте
Base.metadata.create_all(bind=postgres_engine)

# Глобальный экземпляр ClickHouse клиента
db = ClickHouseClient()