#include <iostream>
#include <filesystem>
#include <thread>
#include <chrono>
#include <regex>

namespace fs = std::filesystem;

int main() {
    const fs::path proc_path{"/proc"};
    const std::regex pid_re("^[0-9]+$");

    while (true) {
        try {
            for (const auto& entry : fs::directory_iterator(proc_path)) {
                if (!entry.is_directory()) continue;

                const std::string name = entry.path().filename().string();
                if (std::regex_match(name, pid_re)) {
                    std::cout << entry.path() << "\n";
                }
            }
        } catch (const fs::filesystem_error& e) {
            std::cerr << "filesystem_error: " << e.what() << "\n";
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(5000));
    
    }
}
