#pragma once
#include<vector>
#include <iostream>
#include <filesystem>
#include <chrono>
#include <regex>
#include "monitoring-agent/domain/ProcessInfo.hpp"
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace fs = std::filesystem;

class ProcessesMonitor
{
private:
    const fs::path proc_path{"/proc"};
    const std::regex pid_re{"^[0-9]+$"};
    #ifdef _WIN32
    const pid_t curr_pid{GetCurrentProcessId()};
    #else
    const pid_t curr_pid{getpid()};
    #endif

    #ifdef _WIN32
    void fillMainInfoProcess(const ProcessInfo& ProcessInfo);
    #else
    void fillMainInfoProcess(const ProcessInfo& ProcessInfo,const fs::path& path);
    #endif

public:
    std::vector<ProcessInfo> getInfoProcess();
    ProcessesMonitor(/* args */);
    ~ProcessesMonitor(/* args */);


};
