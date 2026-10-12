cmake_minimum_required(VERSION 3.14)
project(gesture_studio_crossplatform LANGUAGES CXX)

set(BINARY_NAME "GestureStudioCrossPlatform")

cmake_policy(SET CMP0079 NEW)

# Standard C++20 for modern thread synchronization and FFI bridges
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Options configured by build system.
set(FLUTTER_MANAGED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/flutter")

# Flutter library and tool build infrastructure.
if(EXISTS "${FLUTTER_MANAGED_DIR}")
    add_subdirectory(${FLUTTER_MANAGED_DIR})
endif()

# Application build; can be modified, but keep the structure.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/runner/CMakeLists.txt")
    add_subdirectory("runner")
endif()

# Generated plugin build library.
set(PLUGIN_BUNDLED_LIBRARIES "")
if(EXISTS "${FLUTTER_MANAGED_DIR}/ephemeral/plugins")
    add_subdirectory(${FLUTTER_MANAGED_DIR}/ephemeral/plugins plugins)
endif()

# Target linking: Include Windows Media Foundation (IMFMediaSource, MFEnumDeviceSources)
# for native DirectShow & Media Foundation dynamic webcam enumeration
if(TARGET ${BINARY_NAME})
    target_link_libraries(${BINARY_NAME} PRIVATE 
        $<$<TARGET_EXISTS:flutter>:flutter> 
        $<$<TARGET_EXISTS:flutter_wrapper_app>:flutter_wrapper_app>
        ${PLUGIN_BUNDLED_LIBRARIES}
        mf.lib
        mfplat.lib
        mfreadwrite.lib
        mfuuid.lib
        shlwapi.lib
    )
endif()
