#include "monitoring-agent/core/processes_monitor.hpp"

ProcessesMonitor::ProcessesMonitor()
{
}

ProcessesMonitor::~ProcessesMonitor()
{
}


void ProcessesMonitor::fillMainInfoProcess(const process_info& process_info,const fs::path& path){
     path.filename().string().assign(process_info.name);
}


std::vector<process_info> ProcessesMonitor::getInfoProcess()
{
    std::vector<process_info> processes_info;
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
                process_info process_info;

                process_info.pid = std::stol(name);
                processes_info.push_back(process_info);

            }
        }

        return processes_info;
    }
    catch (const fs::filesystem_error &e)
    {
        std::cerr << "filesystem_error: " << e.what() << "\n";
    }
}