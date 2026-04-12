// SPDX-License-Identifier: GPL-2.0
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

/* ── Константы ────────────────────────────────────────────── */
#define ETH_P_IP      0x0800
#define IPPROTO_TCP   6
#define IPPROTO_UDP   17
#define IPPROTO_ICMP  1

#define HOOK_TC         0
#define HOOK_XDP        1
#define HOOK_CGROUP_SKB 2

#define DIR_INGRESS 0
#define DIR_EGRESS  1

/* ── Структура события ────────────────────────────────────── */
struct packet_event {
    __u64 timestamp_ns;
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u32 pkt_len;
    __u8  protocol;
    __u8  hook_type;
    __u8  direction;
    __u8  pad;
    __u32 ifindex;
} __attribute__((packed));

/* ── Perf-event map (ядро ≥ 4.3) ─────────────────────────── */
struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} events SEC(".maps");

/* ═══════════════════════════════════════════════════════════
   Парсинг пакетов
   ═══════════════════════════════════════════════════════════ */

/* Парсинг ethernet → ip → L4 (для TC / XDP — данные с eth-заголовком) */
static __always_inline int
parse_eth_ip(void *data, void *data_end, struct packet_event *evt)
{
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return -1;

    if (bpf_ntohs(eth->h_proto) != ETH_P_IP)
        return -1;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return -1;

    evt->src_ip   = ip->saddr;
    evt->dst_ip   = ip->daddr;
    evt->protocol = ip->protocol;
    evt->pkt_len  = bpf_ntohs(ip->tot_len);

    __u32 ip_hlen = ip->ihl * 4;
    void *l4      = (void *)ip + ip_hlen;

    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = l4;
        if ((void *)(tcp + 1) > data_end)
            return 0; /* IP parsed, ports unknown — OK */
        evt->src_port = bpf_ntohs(tcp->source);
        evt->dst_port = bpf_ntohs(tcp->dest);
    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = l4;
        if ((void *)(udp + 1) > data_end)
            return 0;
        evt->src_port = bpf_ntohs(udp->source);
        evt->dst_port = bpf_ntohs(udp->dest);
    }
    return 0;
}

/* Парсинг IP → L4 через bpf_skb_load_bytes (cgroup_skb — без eth) */
static __always_inline int
parse_skb_ip(struct __sk_buff *skb, struct packet_event *evt)
{
    struct iphdr ip;
    if (bpf_skb_load_bytes(skb, 0, &ip, sizeof(ip)) < 0)
        return -1;
    if (ip.version != 4)
        return -1;

    evt->src_ip   = ip.saddr;
    evt->dst_ip   = ip.daddr;
    evt->protocol = ip.protocol;
    evt->pkt_len  = bpf_ntohs(ip.tot_len);

    __u32 ip_hlen = ip.ihl * 4;

    if (ip.protocol == IPPROTO_TCP) {
        struct tcphdr tcp;
        if (bpf_skb_load_bytes(skb, ip_hlen, &tcp, sizeof(tcp)) < 0)
            return 0;
        evt->src_port = bpf_ntohs(tcp.source);
        evt->dst_port = bpf_ntohs(tcp.dest);
    } else if (ip.protocol == IPPROTO_UDP) {
        struct udphdr udp;
        if (bpf_skb_load_bytes(skb, ip_hlen, &udp, sizeof(udp)) < 0)
            return 0;
        evt->src_port = bpf_ntohs(udp.source);
        evt->dst_port = bpf_ntohs(udp.dest);
    }
    return 0;
}

/* ═══════════════ TC CLASSIFIER ═══════════════════════════ */

SEC("classifier/ingress")
int tc_cls_ingress(struct __sk_buff *skb)
{
    struct packet_event evt = {};
    evt.timestamp_ns = bpf_ktime_get_ns();
    evt.hook_type    = HOOK_TC;
    evt.direction    = DIR_INGRESS;
    evt.ifindex      = skb->ifindex;

    void *data     = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;

    if (parse_eth_ip(data, data_end, &evt) < 0)
        return 0; /* TC_ACT_OK */

    bpf_perf_event_output(skb, &events, BPF_F_CURRENT_CPU,
                          &evt, sizeof(evt));
    return 0;
}

SEC("classifier/egress")
int tc_cls_egress(struct __sk_buff *skb)
{
    struct packet_event evt = {};
    evt.timestamp_ns = bpf_ktime_get_ns();
    evt.hook_type    = HOOK_TC;
    evt.direction    = DIR_EGRESS;
    evt.ifindex      = skb->ifindex;

    void *data     = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;

    if (parse_eth_ip(data, data_end, &evt) < 0)
        return 0;

    bpf_perf_event_output(skb, &events, BPF_F_CURRENT_CPU,
                          &evt, sizeof(evt));
    return 0;
}

/* ═══════════════ XDP ═════════════════════════════════════ */

SEC("xdp")
int xdp_traffic(struct xdp_md *ctx)
{
    struct packet_event evt = {};
    evt.timestamp_ns = bpf_ktime_get_ns();
    evt.hook_type    = HOOK_XDP;
    evt.direction    = DIR_INGRESS;
    evt.ifindex      = ctx->ingress_ifindex;

    void *data     = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    if (parse_eth_ip(data, data_end, &evt) < 0)
        return XDP_PASS;

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU,
                          &evt, sizeof(evt));
    return XDP_PASS;
}

/* ═══════════════ CGROUP SKB ══════════════════════════════ */

SEC("cgroup_skb/ingress")
int cg_skb_ingress(struct __sk_buff *skb)
{
    struct packet_event evt = {};
    evt.timestamp_ns = bpf_ktime_get_ns();
    evt.hook_type    = HOOK_CGROUP_SKB;
    evt.direction    = DIR_INGRESS;
    evt.ifindex      = skb->ifindex;

    if (parse_skb_ip(skb, &evt) < 0)
        return 1; /* allow */

    bpf_perf_event_output(skb, &events, BPF_F_CURRENT_CPU,
                          &evt, sizeof(evt));
    return 1;
}

SEC("cgroup_skb/egress")
int cg_skb_egress(struct __sk_buff *skb)
{
    struct packet_event evt = {};
    evt.timestamp_ns = bpf_ktime_get_ns();
    evt.hook_type    = HOOK_CGROUP_SKB;
    evt.direction    = DIR_EGRESS;
    evt.ifindex      = skb->ifindex;

    if (parse_skb_ip(skb, &evt) < 0)
        return 1;

    bpf_perf_event_output(skb, &events, BPF_F_CURRENT_CPU,
                          &evt, sizeof(evt));
    return 1;
}

char _license[] SEC("license") = "GPL";
struct packet_event *unused_evt __attribute__((unused));