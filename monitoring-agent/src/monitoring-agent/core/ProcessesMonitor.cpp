#include "monitoring-agent/core/ProcessesMonitor.hpp"

ProcessesMonitor::ProcessesMonitor()
{
}

ProcessesMonitor::~ProcessesMonitor()
{
}


void ProcessesMonitor::fillMainInfoProcess(const ProcessInfo& ProcessInfo,const fs::path& path){
     path.filename().string().assign(ProcessInfo.name);
}


std::vector<ProcessInfo> ProcessesMonitor::getInfoProcess()
{
    std::vector<ProcessInfo> processes_info;
    try
    {
        for (const auto &entry : fs::directory_iterator(proc_path))
        {
            if (!entry.is_directory())
                continue;

            const fs::path path = entry.path();
            const std::string name = path.filename().string();
            
            if (name == std::to_string(curr_pid))
                continue;            

            if (std::regex_match(name, pid_re))
            {
                ProcessInfo ProcessInfo;

                ProcessInfo.pid = std::stol(name);
                processes_info.push_back(ProcessInfo);

            }
        }

        return processes_info;
    }
    catch (const fs::filesystem_error &e)
    {
        std::cerr << "filesystem_error: " << e.what() << "\n";
    }
}