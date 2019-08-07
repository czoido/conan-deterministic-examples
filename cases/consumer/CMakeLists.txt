cmake_minimum_required(VERSION 3.0)
project(DetlibConsumerConan)

SET(CMAKE_CXX_STANDARD 11)
SET(CMAKE_CXX_STANDARD_REQUIRED ON)

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup()

add_executable(detconsumer src/main.cpp)
target_link_libraries(detconsumer ${CONAN_LIBS})
