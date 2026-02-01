#pragma once
#include <cstdint>
#include <string>

struct NetConnectionInfo
{
    // 1) Временная привязка (для polling)
    uint64_t snapshot_time_ns = 0;
    uint64_t first_seen_ns = 0;
    uint64_t last_seen_ns  = 0;
    uint32_t observed_count = 0;

    // 2) Привязка к процессу (после сопоставления inode -> pid/fd)
    int32_t pid = -1;          // владелец (после join)
    int32_t fd  = -1;          // если нашли конкретный fd у процесса, иначе -1

    // 3) Тип соединения
    enum class transport : uint8_t { unknown=0, tcp, udp, raw, other } proto = transport::unknown;

    // 4) IP-адреса/порты (универсально для v4/v6)
    enum class ip_version : uint8_t { none=0, v4, v6 } ip_ver = ip_version::none;

    std::string local_ip;
    uint16_t    local_port = 0;

    std::string remote_ip;   // может быть пусто/0.0.0.0 для LISTEN/неподключённых
    uint16_t    remote_port = 0;

    // 5) TCP-специфика
    uint32_t tcp_state = 0;  // числовой state из /proc/net/tcp*
    uint32_t tcp_retransmits = 0; // если можете извлечь (не всегда есть в /proc)

    // 6) Идентификатор сокета для склейки с FD
    uint64_t socket_inode = 0; // inode из /proc/net/*, совпадает с "socket:[inode]" в /proc/<pid>/fd

    // 7) Роль сокета
    bool is_listen = false;    // для TCP: state == LISTEN (вычисляете)
    bool is_loopback = false;  // local/remote лежат в 127.0.0.0/8 или ::1 (вычисляете)

};
