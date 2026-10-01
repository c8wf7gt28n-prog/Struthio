# STRUTHIO HANDHELD · Prototype A0 firmware (ESP-IDF >= 5.5, ESP32-S3).
#   cd handheld/firmware && idf.py set-target esp32s3 && idf.py build flash monitor
cmake_minimum_required(VERSION 3.16)
set(EXTRA_COMPONENT_DIRS ${CMAKE_CURRENT_LIST_DIR}/components)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(struthio_a0)
