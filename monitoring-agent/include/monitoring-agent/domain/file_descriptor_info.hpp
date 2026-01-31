#pragma once
#include <cstdint>
#include <string>
#include <optional>

struct file_descriptor_info
{
    
    int32_t fd  = -1;
    // 2) Временные поля наблюдения (для polling это критично)
    uint64_t snapshot_time_ns = 0;   // время текущего опроса
    uint64_t first_seen_ns = 0;      // когда впервые увидели этот FD (в вашей системе)
    uint64_t last_seen_ns  = 0;      // когда последний раз видели (обычно = snapshot_time_ns)

    // 3) Классификация объекта
    enum class fd_kind : uint8_t {
        unknown = 0,
        regular_file,
        directory,
        char_device,
        block_device,
        fifo_pipe,
        unix_socket,
        inet_socket,
        netlink_socket,
        anon_inode,
        memfd,
        eventfd,
        signalfd,
        timerfd,
        inotify,
        fanotify,
        pidfd,
        other
    } kind = fd_kind::unknown;

    // 4) "Куда указывает" дескриптор (из /proc/<pid>/fd/<fd>)
    std::string proc_target;     // readlink: "/etc/passwd", "socket:[123]", "anon_inode:[eventpoll]"
    std::string resolved_path;   // если удалось привести к пути (учитывая root/mount ns)

    // 5) Устойчивые идентификаторы объекта (из fstat)
    uint64_t inode = 0;          // st_ino
    uint32_t dev_major = 0;      // major(st_dev)
    uint32_t dev_minor = 0;      // minor(st_dev)

    uint32_t mode = 0;           // st_mode (тип+права)
    uint32_t uid  = 0;           // st_uid
    uint32_t gid  = 0;           // st_gid

    uint64_t size_bytes = 0;     // st_size (для файлов)
    uint64_t mtime_ns = 0;       // st_mtim
    uint64_t ctime_ns = 0;       // st_ctim

    // 5) Атрибуты именно "FD", а не файла (fcntl + /proc/<pid>/fdinfo/<fd>)
    uint64_t open_flags = 0;     // fcntl(F_GETFL): O_RDONLY/O_WRONLY/O_RDWR, O_APPEND, O_NONBLOCK...
    uint64_t fd_flags   = 0;     // fcntl(F_GETFD): FD_CLOEXEC и др.
    uint64_t file_pos   = 0;     // fdinfo: "pos:"
    uint64_t fdinfo_flags = 0;   // fdinfo: "flags:" (часто дублирует open_flags, но полезно для сверки)

    // 6) Полезные детект-сигналы "без статусов"
    bool is_deleted = false;     // proc_target содержит " (deleted)" или по косвенным признакам
    bool is_execve_capable = false; // если это regular_file и есть execute bit (из mode) — чисто факт

    // 7) Memory map корреляция (если вы анализируете /proc/<pid>/maps)
    bool     is_mapped = false;
    uint64_t mapped_bytes = 0;
    uint32_t mapped_prot_mask = 0; // битовая маска R/W/X (например 1=R,2=W,4=X)

};