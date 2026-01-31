#pragma once
#include<vector>
#include "domain/process_info.hpp"
class ProcessesMonitor
{
private:
    /* data */
public:
    std::vector<process_info> getInfoProcess();
    ProcessesMonitor(/* args */);
    ~ProcessesMonitor(/* args */);


};
