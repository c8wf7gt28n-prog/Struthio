# STRUTHIO HANDHELD firmware (ESP-IDF 5.5.x, ESP32-S3).
#   cd handheld/firmware && idf.py set-target esp32s3 && idf.py build flash monitor
# Picture:  idf.py -D STRUTHIO_ART=greybox build flash   (first-boot test: flat colours)
#           idf.py -D STRUTHIO_ART=full build flash      (the real art; the default)
cmake_minimum_required(VERSION 3.16)
set(EXTRA_COMPONENT_DIRS ${CMAKE_CURRENT_LIST_DIR}/components)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(struthio)

# The asset pack (textures and HUD at panel density, from the browser's own
# output): build it on the host with `make -C ../host pak`; `idf.py flash`
# then writes it to the 'assets' partition. Without it the firmware runs the
# greybox renderer.
set(STRUTHIO_ASSETS ${CMAKE_CURRENT_LIST_DIR}/../build/assets)
set(STRUTHIO_PAK ${STRUTHIO_ASSETS}/struthio.pak)
set(STRUTHIO_ART "full" CACHE STRING "full: flash the art pack; greybox: flash a greybox marker instead")
set_property(CACHE STRUTHIO_ART PROPERTY STRINGS full greybox)
# Adding, removing or renaming a file in build/assets changes the folder, which
# re-runs this configure step, so the next build flashes what is there now.
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${STRUTHIO_ASSETS})
if(STRUTHIO_ART STREQUAL "greybox")
    # an 8-byte marker overwrites the start of the assets partition, so a board
    # that already holds the art also shows the greybox picture
    set(STRUTHIO_GREY ${CMAKE_BINARY_DIR}/greybox_marker.bin)
    file(WRITE ${STRUTHIO_GREY} "STRGREY0")
    esptool_py_flash_to_partition(flash "assets" "${STRUTHIO_GREY}")
    message(STATUS "STRUTHIO_ART=greybox: flashing the greybox marker, not the art pack")
elseif(EXISTS ${STRUTHIO_PAK})
    esptool_py_flash_to_partition(flash "assets" "${STRUTHIO_PAK}")
    message(STATUS "STRUTHIO_ART=full: flashing ${STRUTHIO_PAK}")
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
