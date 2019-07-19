cmake_minimum_required(VERSION 3.0)
project(DeterministicHello)

SET(CMAKE_CXX_STANDARD 11)
SET(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(det_hello STATIC ./src/mydetlib.cpp ./include/mydetlib.hpp)
