#!/bin/sh
# STRUTHIO - put the game on the board (macOS / Linux). Run:  ./flash_me.sh
# Installs esptool (Espressif's flashing tool) the first time, finds the board on USB by itself, writes the
# game, its pictures and its music, and checks every byte. Nothing here needs ESP-IDF.
cd "$(dirname "$0")/prebuilt" 2>/dev/null || { echo "Keep this file in the STRUTHIO folder, next to 'prebuilt'."; exit 1; }
echo
echo "  STRUTHIO - put the game on the board"
echo
PY=python3
command -v $PY >/dev/null 2>&1 || { echo "  Python 3 is missing: install it from https://www.python.org/downloads/ and run this again."; exit 1; }
echo "  [1/4] Python: ok"
if ! $PY -m esptool version >/dev/null 2>&1; then
  echo "  [2/4] Installing esptool (once, about 30 s)..."
  $PY -m pip install --user --quiet --disable-pip-version-check "esptool>=5" || $PY -m pip install --user --quiet --break-system-packages "esptool>=5"
fi
$PY -m esptool version >/dev/null 2>&1 || { echo "  esptool could not be installed: check the internet connection."; exit 1; }
echo "  [2/4] esptool: ok"
PORT=${STRUTHIO_PORT:-}                     # optional: name the port yourself
while [ -z "$PORT" ]; do
  PORT=$(ls /dev/cu.usbmodem* /dev/ttyACM* 2>/dev/null | head -n 1)
  [ -n "$PORT" ] && break
  echo "  [3/4] No board found on USB. Plug it in with a USB-C DATA cable (or put it in download mode:"
  echo "        hold BOOT, press and release RESET, release BOOT), then press Enter."
  read _
done
echo "  [3/4] Board found on $PORT"
echo "  [4/4] Writing the game, its pictures and its music (about 2 minutes)..."
if $PY -m esptool --chip esp32s3 -p "$PORT" -b 460800 write-flash @flash_args.txt; then
  echo
  echo "  DONE. Every file was written and checked. Unplug the board, or press RESET: the first power-on check starts."
else
  echo
  echo "  Flashing stopped. Put the board in download mode (hold BOOT, press and release RESET, release BOOT)"
  echo "  and run ./flash_me.sh again. Nothing else was changed."
  exit 1
fi
