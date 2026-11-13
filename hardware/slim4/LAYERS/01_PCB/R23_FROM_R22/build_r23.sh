#!/bin/sh
# Rebuild the R23 board from the R22 board: R22 -> R23 edits, each in its own pcbnew process (KiCad 7.0.x,
# python3 with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r23.sh <path to a copy of SLIM4_R22.kicad_pcb renamed SLIM4_R23.kicad_pcb, beside SLIM4.pretty and fp-lib-table>
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
edit() { python3 "$S/run_edit.py" "$B" "$S/$1.py" 2>&1 | grep -v leak || true; }
edit r23_battery                                                       # 12 battery: JST PH socket, reverse-polarity FET
edit r23_speakers                                                      # 13 speakers: PicoBlade sockets
python3 "$S/r23_values.py" "$B"                                        # 14 charge current, backlight current
edit r23_display_a                                                     # 15A display port J1 on the front, cleared copper
edit r23_display_b                                                     # 15B battery window, J1 fan-out
edit r23_display_c0                                                    # 15C0 DSI back to R301-R306 stubs
edit r23_display_c                                                     # 15C routed copper (r23_display_c.json)
edit r23_display_d                                                     # 15D stub clean-up, unlock
python3 "$S/r23_lib_sync.py" "$B" "$(dirname "$B")/SLIM4.pretty" 2>&1 | grep -v leak || true
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                # zone refill + KiCad DRC
