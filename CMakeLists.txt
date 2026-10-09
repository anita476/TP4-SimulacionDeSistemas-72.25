cmake_minimum_required(VERSION 3.16)

project(TimeDriven-TP4 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

include(FetchContent)

FetchContent_Declare(
    argparse
    GIT_REPOSITORY https://github.com/p-ranav/argparse.git
    GIT_TAG v3.2
)

FetchContent_MakeAvailable(argparse)

add_library(sim_core_table STATIC
    src/utils/obstacle.cpp
    src/utils/generator.cpp
    src/utils/billiard.cpp
)

add_library(sim_core_oscillator STATIC
    src/utils/methods.cpp
)

# Add include directories to a target.
target_include_directories(sim_core_table PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/utils/include
)

target_include_directories(sim_core_oscillator PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/utils/include
)

add_executable(TimeDrivenSimTable
    src/table_main.cpp
)
add_executable(TimeDrivenSimOscillator
    src/oscillator_main.cpp
)

target_link_libraries(TimeDrivenSimTable PRIVATE
    sim_core_table
    argparse
)

target_link_libraries(TimeDrivenSimOscillator PRIVATE 
    sim_core_oscillator
    argparse
)