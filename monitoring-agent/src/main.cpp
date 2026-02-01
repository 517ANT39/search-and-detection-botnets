#include<iostream>
#include"monitoring-agent/core/ProcessesMonitor.hpp"
#include<chrono>
#include<thread>
int main() {
    ProcessesMonitor pm;
    while (true) {
        auto res = pm.getInfoProcess();

        for (const auto& item : res)
        {
            std::cout << item.pid << std::endl;
        }        
           
        std::this_thread::sleep_for(std::chrono::milliseconds(5000));
    
    }
}
