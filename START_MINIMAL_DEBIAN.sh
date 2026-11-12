#!/usr/bin/env bash
# Start one dedicated graphical Graphite session from a Debian text login.
# From an existing display it opens the fullscreen Office in that desktop instead
# (arguments forwarded, no second X server, the dedicated-session marker not set).
# From a text login it takes no arguments, checks startx, fluxbox, dbus-run-session
# and an X server, runs startx with LS_XSESSION.sh, then reads back the status that
# LS_XSESSION.sh recorded (xinit itself returns 0 whatever Graphite did) and exits with it.
set -euo pipefail
ledger_program="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${EUID}" == 0 ]]; then echo 'Start Graphite as your ordinary user, not root.' >&2; exit 1; fi
if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
  export ARC_LEDGER_FULLSCREEN=1
  exec bash "$ledger_program/START_OFFICE.sh" "$@"
fi
if [[ $# -gt 0 ]]; then
  echo "The dedicated session takes no arguments (got: $*). From a text login run START_MINIMAL_DEBIAN.sh alone; options such as --doctor or --version work with: bash $ledger_program/START_OFFICE.sh $*" >&2; exit 1
fi
for ledger_command in startx fluxbox dbus-run-session; do
  command -v "$ledger_command" >/dev/null || { echo "Missing $ledger_command. Run INSTALL_DEBIAN.sh --minimal-session --quick, or install the matching USB prerequisites." >&2; exit 1; }
done
command -v Xorg >/dev/null || command -v X >/dev/null || { echo 'Missing an X server (Xorg). Run INSTALL_DEBIAN.sh --minimal-session --quick, or install the matching USB prerequisites.' >&2; exit 1; }
ledger_record="${XDG_STATE_HOME:-$HOME/.local/state}/ledger-slate/last-session.json"
rm -f -- "$ledger_record" 2>/dev/null || true
ledger_rc=0
startx "$ledger_program/LS_XSESSION.sh" -- || ledger_rc=$?
ledger_python=python3
if ! command -v python3 >/dev/null && [[ -x "$ledger_program/.venv/bin/python" ]]; then ledger_python="$ledger_program/.venv/bin/python"; fi
ledger_line=''
if [[ -f "$ledger_record" ]]; then
  ledger_line="$("$ledger_python" -I -c 'import json,sys
data=json.load(open(sys.argv[1]));status=data["status"]
assert type(status) is int and 0<=status<=255
log=data.get("log");print(status,("details: "+log) if isinstance(log,str) and log else "")' "$ledger_record" 2>/dev/null)" || ledger_line=''
fi
if [[ -n "$ledger_line" ]]; then
  ledger_status="${ledger_line%% *}"; ledger_details="${ledger_line#* }"
  echo "Graphite ended with status ${ledger_status}${ledger_details:+ · $ledger_details}"
  exit "$ledger_status"
fi
echo "Graphite session ended; status not recorded (startx returned $ledger_rc)." >&2
exit $(( ledger_rc == 0 ? 1 : ledger_rc ))
