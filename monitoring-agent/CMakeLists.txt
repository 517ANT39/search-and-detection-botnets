# Минимальная версия CMake
cmake_minimum_required(VERSION 3.10)

# Название проекта
project(monitoring_agent LANGUAGES CXX)

# Установка директории заголовков
include_directories(${CMAKE_SOURCE_DIR}/include)

# Добавляем исходники в проект
set(SOURCE_FILES
    src/main.cpp
    src/monitoring-agent/core/processes_monitor.cpp
)

# Создаем исполнимый файл
add_executable(monitoring_agent ${SOURCE_FILES})