cmake_minimum_required(VERSION 3.14)
project(runner LANGUAGES CXX)

add_executable(${BINARY_NAME} WIN32
  "main.cpp"
)

target_compile_definitions(${BINARY_NAME} PRIVATE
  $<$<CONFIG:Debug>:DEBUG>
)
