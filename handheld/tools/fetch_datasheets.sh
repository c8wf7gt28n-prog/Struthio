#!/bin/sh
# STRUTHIO HANDHELD · download the manufacturers' documents behind
# docs/HARDWARE_FACTS.md and check they are the versions the facts were read from.
#   sh tools/fetch_datasheets.sh [OUT_DIR]      (default: build/datasheets)
set -e
OUT=${1:-"$(dirname "$0")/../build/datasheets"}
mkdir -p "$OUT"; cd "$OUT"
W=https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-3.5B
get() { curl -fsSL -o "$1" "$2" && echo "got  $1"; }
get ESP32-S3-Touch-LCD-3.5B_V2.0.pdf      $W/ESP32-S3-Touch-LCD-3.5B_V2.0.pdf
get ESP32-S3-Touch-LCD-3.5B-Schematic.pdf $W/ESP32-S3-Touch-LCD-3.5B-Schematic.pdf
get size_bare_board.webp https://docs.waveshare.com/assets/images/ESP32-S3-Touch-LCD-3.5B-details-size-1-ceb0bb9af8bcc0e1bfe44210143033e1.webp
get size_cased_C.webp    https://docs.waveshare.com/assets/images/ESP32-S3-Touch-LCD-3.5B-details-size-c58333b4af38d04a25ef2d68ee5dbd8e.webp
get 500SSP1S1M7QEA.pdf https://configured-product-images.s3.amazonaws.com/2D/specs/500SSP1S1M7QEA.pdf
get E-Switch_500.pdf   https://configured-product-images.s3.amazonaws.com/Datasheets/500.pdf
get AS02808MR-R.pdf    https://api.puiaudio.com/filename/AS02808MR-R.pdf
check() { s=$(sha256sum "$1" | cut -c1-16); [ "$s" = "$2" ] && echo "ok   $1" || echo "NEW  $1 ($s): re-read it against docs/HARDWARE_FACTS.md"; }
check ESP32-S3-Touch-LCD-3.5B_V2.0.pdf      a0b65d8be900a401
check ESP32-S3-Touch-LCD-3.5B-Schematic.pdf 71fe3528189c6242
check size_bare_board.webp ce448ce06c3665db
check size_cased_C.webp    1c4953f7e3625b22
check 500SSP1S1M7QEA.pdf   57d0ea1c47d45d63
check E-Switch_500.pdf     a46cf77d0dac1a82
check AS02808MR-R.pdf      9745b0373bdd5e52
