#pragma once
#include<string>
#include<vector>
#include"NetConnectionInfo.hpp"
#include"FileDescriptorInfo.hpp"

struct ProcessInfo
{
    pid_t pid;
    pid_t parent_pid;
    uid_t uid;
    std::string name; // Имя процесса
    std::string cmdline; // Полная командная строка
    std::string user_run; // Имя пользователя

    // CPU статистика
    unsigned long utime;      // Время в user mode (в тиках)
    unsigned long stime;      // Время в kernel mode (в тиках)
    unsigned long start_time; // Время запуска
    unsigned int cpu_percent; // Процент CPU

    // Память
    unsigned long vsize;      // Виртуальная память (байты)
    unsigned long rss;                 // Резидентная память (страницы)
    unsigned long shared;     // Разделяемая память
    unsigned int mem_percent;       // Процент памяти

    std::vector<NetConnectionInfo> NetConnectionInfos;
    std::vector<FileDescriptorInfo> FileDescriptorInfos;

};
