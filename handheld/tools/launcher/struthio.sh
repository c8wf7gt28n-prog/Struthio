#!/usr/bin/env bash
# ==========================================================================
#  STRUTHIO HANDHELD - build menu for macOS, Linux and WSL
#    ./struthio.sh            (from the unzipped STRUTHIO folder)
#  Every option prints the exact command it runs, so you learn the commands
#  the build manual uses while the menu types them for you.
# ==========================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HH="$ROOT/handheld"
FW="$HH/firmware"
PORTFILE="$ROOT/struthio_port.txt"
PORT="$( [ -f "$PORTFILE" ] && head -n1 "$PORTFILE" | tr -d '\r' || true )"

[ -f "$FW/CMakeLists.txt" ] || { echo "Keep struthio.sh in the STRUTHIO folder, next to 'handheld'."; exit 1; }
case "$ROOT" in *" "*) echo "WARNING: the folder path contains a space ($ROOT). Move it to ~/struthio."; read -r -p "Enter to continue " _;; esac

find_idf() {
  command -v idf.py >/dev/null 2>&1 && return 0
  for e in "${IDF_PATH:-}/export.sh" "$HOME/esp/esp-idf/export.sh" "$HOME/esp/v5.5.5/esp-idf/export.sh"; do
    if [ -f "$e" ]; then echo "Activating ESP-IDF: . $e"; . "$e" >/dev/null; break; fi
  done
  command -v idf.py >/dev/null 2>&1
}
need_idf() {
  find_idf && return 0
  echo; echo "ESP-IDF was not found. In this terminal run:  . ~/esp/esp-idf/export.sh"
  echo "(Install ESP-IDF 5.5.x first if you have not: flashing guide, section 4.)"; return 1
}
py() { command -v python3 >/dev/null 2>&1 && echo python3 || echo python; }
need_port() { [ -n "$PORT" ] && return 0; echo; echo "Choose the board's port first (option 2)."; return 1; }
ensure_target() {
  [ -f "$FW/sdkconfig" ] && return 0
  echo; echo "First build in this folder: choosing the chip."
  run idf.py -C "$FW" set-target esp32s3
}
run() { echo; echo "> $*"; "$@"; }
pause() { echo; read -r -p "Press Enter for the menu " _; }

while true; do
  clear
  echo "  ==============================================================="
  echo "    STRUTHIO HANDHELD  -  build menu"
  echo "  ==============================================================="
  if command -v idf.py >/dev/null 2>&1; then echo "    ESP-IDF : ready"; else echo "    ESP-IDF : not active - option 1 explains"; fi
  if [ -n "$PORT" ]; then echo "    Board   : $PORT"; else echo "    Board   : not chosen yet - option 2"; fi
  cat <<'MENU'
  ---------------------------------------------------------------
    G  PUT THE GAME ON THE BOARD   (ready-made, no ESP-IDF needed)
  ---------------------------------------------------------------
    1  Check my setup              (doctor: package, ESP-IDF, port)
    2  Find / choose the board's port
    3  Build the firmware          (first time: sets the chip)
    4  GREYBOX test   - build, flash, watch the log
    5  FULL ART       - build, flash, watch the log
    6  Quick flash    - program only, keeps art + music
    7  Watch the log  (monitor)     leave with Ctrl + ]
    8  Download-mode help (BOOT + RESET)
    9  Erase the whole board        (clears high score + settings)
    D  Desktop checks      
    0  Exit
  ---------------------------------------------------------------
MENU
  read -r -p "  Choose: " CH
  case "$CH" in
    g|G) PORT="$PORT" STRUTHIO_PORT="$PORT" "$ROOT/flash_me.sh"; pause;;
    1) find_idf >/dev/null 2>&1; run "$(py)" "$HH/tools/struthio_doctor.py"; pause;;
    2) find_idf >/dev/null 2>&1
       FOUND="$("$(py)" "$HH/tools/struthio_doctor.py" --port 2>/dev/null)"
       if [ -n "$FOUND" ]; then echo; echo "Found the board on $FOUND."; PORT="$FOUND"
       else
         echo; echo "Not recognised automatically. Serial ports now:"
         ls /dev/cu.usbmodem* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | sed 's/^/   /'
         echo "Unplug the board, look again, plug it in: the new entry is the board."
         read -r -p "Type the port (e.g. /dev/ttyACM0), or Enter to skip: " NEW
         [ -n "$NEW" ] && PORT="$NEW"
       fi
       [ -n "$PORT" ] && echo "$PORT" > "$PORTFILE"; pause;;
    3) need_idf && ensure_target && run idf.py -C "$FW" build; pause;;
    4) need_idf && need_port && ensure_target && {
         echo; echo "GREYBOX TEST: flat colours on purpose; 'assets: greybox marker' in the log is expected."
         run idf.py -C "$FW" -p "$PORT" -D STRUTHIO_ART=greybox build flash monitor; }; pause;;
    5) need_idf && need_port && ensure_target && {
         echo; echo "FULL ART: program + 8.3 MB art pack + 1.9 MB soundtrack. The first full flash takes a few minutes."
         run idf.py -C "$FW" -p "$PORT" -D STRUTHIO_ART=full build flash monitor; }; pause;;
    6) need_idf && need_port && ensure_target && run idf.py -C "$FW" -p "$PORT" app-flash monitor; pause;;
    7) need_idf && need_port && {
         echo; echo "Monitor keys: Ctrl+] leave | Ctrl+T then Y pause | Ctrl+T then L log file | Ctrl+T then R reset"
         run idf.py -C "$FW" -p "$PORT" monitor; }; pause;;
    8) cat <<'BOOT'

  If flashing says it cannot connect, put the ESP32-S3 in download mode:
    1. Hold the BOOT button on the board.
    2. Press and release RESET (RST) once.
    3. Release BOOT.
    4. Choose the flash option again.
    5. After flashing, press RESET once to run STRUTHIO.
  The port name can change in download mode: run option 2 again if needed.
BOOT
       pause;;
    9) need_idf && need_port && {
         echo; echo "This erases EVERYTHING on the board: program, art, music, high score, DART mode, volume."
         read -r -p "Type ERASE to continue: " SURE
         [ "$SURE" = "ERASE" ] && run idf.py -C "$FW" -p "$PORT" erase-flash; }; pause;;
    d|D) run make -C "$HH/host" test && run make -C "$HH/firmware/host_test" run
       echo; echo "PASS means: 5 lines starting PASS, then 'GOLDEN REPLAY: all 5 traces bit-exact', then 'PASS: wing buttons (...)'."
       pause;;
    0) exit 0;;
  esac
done
