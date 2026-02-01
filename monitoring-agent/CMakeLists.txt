cmake_minimum_required(VERSION 3.10)

project(monitoring_agent LANGUAGES CXX)

add_executable(monitoring_agent)

# 1) Все исходники .cpp только из src/ и его подпапок
file(GLOB_RECURSE MONITORING_AGENT_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_SOURCE_DIR}/src/*.cpp"
)

target_sources(monitoring_agent PRIVATE
    ${MONITORING_AGENT_SOURCES}
)

# 2) Заголовки лежат в include/
target_include_directories(monitoring_agent PRIVATE
    "${CMAKE_SOURCE_DIR}/include"
)

# 3) Стандарт C++
set_target_properties(monitoring_agent PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
