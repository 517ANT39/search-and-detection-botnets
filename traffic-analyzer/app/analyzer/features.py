import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "total_packets", "total_bytes", "avg_pkt_len", "std_pkt_len",
    "unique_dst_ips", "unique_dst_ports", "unique_src_ports",
    "tcp_ratio", "udp_ratio", "icmp_ratio",
    "pps", "bps", "port_diversity",
]


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby(["host_id", "src_ip"]).agg(
        total_packets=("pkt_len", "count"),
        total_bytes=("pkt_len", "sum"),
        avg_pkt_len=("pkt_len", "mean"),
        std_pkt_len=("pkt_len", "std"),
        min_pkt_len=("pkt_len", "min"),
        max_pkt_len=("pkt_len", "max"),
        unique_dst_ips=("dst_ip", "nunique"),
        unique_dst_ports=("dst_port", "nunique"),
        unique_src_ports=("src_port", "nunique"),
        tcp_count=("protocol", lambda x: (x == 6).sum()),
        udp_count=("protocol", lambda x: (x == 17).sum()),
        icmp_count=("protocol", lambda x: (x == 1).sum()),
        ingress_count=("direction", lambda x: (x == 0).sum()),
        egress_count=("direction", lambda x: (x == 1).sum()),
        time_span_sec=("timestamp", lambda x: (x.max() - x.min()).total_seconds() if len(x) > 1 else 0),
    ).reset_index()

    grouped["std_pkt_len"] = grouped["std_pkt_len"].fillna(0)
    grouped["tcp_ratio"] = grouped["tcp_count"] / grouped["total_packets"]
    grouped["udp_ratio"] = grouped["udp_count"] / grouped["total_packets"]
    grouped["icmp_ratio"] = grouped["icmp_count"] / grouped["total_packets"]
    grouped["pps"] = np.where(grouped["time_span_sec"] > 0,
                              grouped["total_packets"] / grouped["time_span_sec"],
                              grouped["total_packets"])
    grouped["bps"] = np.where(grouped["time_span_sec"] > 0,
                              grouped["total_bytes"] / grouped["time_span_sec"],
                              grouped["total_bytes"])
    grouped["port_diversity"] = grouped["unique_dst_ports"] / grouped["total_packets"]

    return grouped
