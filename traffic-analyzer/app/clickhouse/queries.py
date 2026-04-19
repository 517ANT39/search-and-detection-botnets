import logging
import clickhouse_connect
import pandas as pd
from flask import current_app

logger = logging.getLogger("clickhouse")


def _get_client():
    return clickhouse_connect.get_client(
        host=current_app.config["CH_HOST"],
        port=current_app.config["CH_PORT"],
        database=current_app.config["CH_DATABASE"],
        username=current_app.config["CH_USERNAME"],
        password=current_app.config["CH_PASSWORD"],
    )


def _query_rows(sql, params=None):
    try:
        client = _get_client()
        result = client.query(sql, parameters=params or {})
        cols = result.column_names
        return [dict(zip(cols, row)) for row in result.result_rows]
    except Exception as e:
        logger.error("ClickHouse query error: %s", e)
        return []


def _query_df(sql, params=None):
    try:
        client = _get_client()
        return client.query_df(sql, parameters=params or {})
    except Exception as e:
        logger.error("ClickHouse query_df error: %s", e)
        return pd.DataFrame()


def get_hosts():
    return _query_rows("""
        SELECT
            host_id,
            hostname,
            os,
            arch,
            kernel_version,
            interfaces,
            boot_time,
            registered_at
        FROM hosts FINAL
        ORDER BY registered_at DESC
    """)


def get_traffic_summary(minutes=60):
    return _query_rows("""
        SELECT
            host_id,
            count()                       AS total_packets,
            sum(pkt_len)                  AS total_bytes,
            uniqExact(src_ip)             AS unique_src,
            uniqExact(dst_ip)             AS unique_dst,
            sumIf(pkt_len, direction=0)   AS ingress_bytes,
            sumIf(pkt_len, direction=1)   AS egress_bytes,
            countIf(protocol=6)           AS tcp_packets,
            countIf(protocol=17)          AS udp_packets,
            countIf(protocol=1)           AS icmp_packets
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
        GROUP BY host_id
        ORDER BY total_bytes DESC
    """, {"minutes": minutes})


def get_top_talkers(minutes=60, limit=20):
    return _query_rows("""
        SELECT
            IPv4NumToString(src_ip) AS src,
            IPv4NumToString(dst_ip) AS dst,
            count()      AS packets,
            sum(pkt_len) AS bytes
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
        GROUP BY src_ip, dst_ip
        ORDER BY bytes DESC
        LIMIT {limit:UInt32}
    """, {"minutes": minutes, "limit": limit})


def get_protocol_distribution(minutes=60):
    return _query_rows("""
        SELECT protocol, count() AS packets, sum(pkt_len) AS bytes
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
        GROUP BY protocol
        ORDER BY packets DESC
    """, {"minutes": minutes})


def get_traffic_timeline(minutes=60, interval_sec=60):
    return _query_rows("""
        SELECT
            toStartOfInterval(timestamp, INTERVAL {interval:UInt32} SECOND) AS ts,
            count()                AS packets,
            sum(pkt_len)           AS bytes,
            countIf(direction=0)   AS in_packets,
            countIf(direction=1)   AS out_packets
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
        GROUP BY ts ORDER BY ts
    """, {"minutes": minutes, "interval": interval_sec})


def get_packets_for_analysis(window_minutes=10):
    return _query_df("""
        SELECT
            timestamp,
            host_id,
            IPv4NumToString(src_ip) AS src_ip,
            IPv4NumToString(dst_ip) AS dst_ip,
            src_port, dst_port, pkt_len,
            protocol, hook_type, direction, if_index
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
        ORDER BY timestamp
    """, {"minutes": window_minutes})


def get_port_scan_candidates(window_minutes=10, threshold=50):
    return _query_rows("""
        SELECT
            host_id,
            IPv4NumToString(src_ip)       AS src_ip,
            uniqExact(dst_port)           AS unique_ports,
            count()                       AS total_packets,
            groupUniqArray(100)(dst_port) AS sample_ports
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
          AND direction = 0
        GROUP BY host_id, src_ip
        HAVING unique_ports >= {threshold:UInt32}
        ORDER BY unique_ports DESC
    """, {"minutes": window_minutes, "threshold": threshold})


def get_ddos_candidates(window_minutes=5):
    return _query_rows("""
        SELECT
            host_id,
            IPv4NumToString(dst_ip)                  AS dst_ip,
            count() / ({minutes:UInt32} * 60)        AS pps,
            sum(pkt_len) / ({minutes:UInt32} * 60)   AS bps,
            uniqExact(src_ip)                         AS unique_sources,
            count()                                   AS total_packets
        FROM packets
        WHERE timestamp > now() - INTERVAL {minutes:UInt32} MINUTE
          AND direction = 0
        GROUP BY host_id, dst_ip
        ORDER BY pps DESC
    """, {"minutes": window_minutes})
