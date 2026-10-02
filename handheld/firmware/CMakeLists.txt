# STRUTHIO HANDHELD · Prototype A0 firmware (ESP-IDF >= 5.5, ESP32-S3).
#   cd handheld/firmware && idf.py set-target esp32s3 && idf.py build flash monitor
cmake_minimum_required(VERSION 3.16)
set(EXTRA_COMPONENT_DIRS ${CMAKE_CURRENT_LIST_DIR}/components)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(struthio_a0)

# The asset pack (textures and HUD at panel density, from the browser's own
# output): build it on the host with `make -C ../host pak`; `idf.py flash`
# then writes it to the 'assets' partition. Without it the firmware runs the
# greybox renderer.
set(STRUTHIO_PAK ${CMAKE_CURRENT_LIST_DIR}/../build/assets/struthio.pak)
if(EXISTS ${STRUTHIO_PAK})
    esptool_py_flash_to_partition(flash "assets" "${STRUTHIO_PAK}")
else()
    message(WARNING "no ${STRUTHIO_PAK}: flashing without the asset pack (greybox renderer)")
endif()
# The soundtrack (`make -C ../host music`, from the arcade's MP3): written to
# the 'music' partition. Without it the game plays its sound effects only.
set(STRUTHIO_MUSIC ${CMAKE_CURRENT_LIST_DIR}/../build/assets/struthio_music.ima)
if(EXISTS ${STRUTHIO_MUSIC})
    esptool_py_flash_to_partition(flash "music" "${STRUTHIO_MUSIC}")
else()
    message(WARNING "no ${STRUTHIO_MUSIC}: flashing without the soundtrack (sound effects only)")
endif()
