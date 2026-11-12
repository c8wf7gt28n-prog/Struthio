#!/usr/bin/env bash
# Private session client: leave Debian login files and other desktops untouched.
# Runs START_OFFICE.sh once in the foreground, then records Graphite's exit status
# in ${XDG_STATE_HOME:-$HOME/.local/state}/ledger-slate/last-session.json so
# START_MINIMAL_DEBIAN.sh can read it back (xinit discards the client status),
# and exits with that status. Nothing here restarts Graphite, logs out or powers off.
set -euo pipefail
ledger_program="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${DISPLAY:-}" ]]; then echo 'Use START_MINIMAL_DEBIAN.sh from a text login.' >&2; exit 1; fi
if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
  exec dbus-run-session -- bash "$ledger_program/LS_XSESSION.sh"
fi
ledger_state_dir="${XDG_STATE_HOME:-${HOME:-}/.local/state}/ledger-slate"
ledger_session_marker="$ledger_state_dir/.session-start"
ledger_session_record() {
  # Write {"status","utc","log"}; a failure to write never changes the exit status.
  {
    local status="$1" log='' json_log='null' candidate
    for candidate in "$ledger_state_dir/launch-error.log" "$(dirname -- "$ledger_program")/launch-error.log"; do
      # Only a log written during this session (not older than the start marker) is named.
      if [[ -f "$candidate" ]] && ! [[ "$candidate" -ot "$ledger_session_marker" ]]; then log="$candidate"; break; fi
    done
    if [[ -n "$log" ]]; then log="${log//\\/\\\\}"; log="${log//\"/\\\"}"; json_log="\"$log\""; fi
    printf '{"status":%d,"utc":"%s","log":%s}\n' "$status" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$json_log" > "$ledger_state_dir/last-session.json.tmp" \
      && mv -f "$ledger_state_dir/last-session.json.tmp" "$ledger_state_dir/last-session.json"
  } 2>/dev/null || true
}
{ mkdir -p "$ledger_state_dir" && : > "$ledger_session_marker"; } 2>/dev/null || true
fluxbox -no-slit -no-toolbar &
ledger_window_manager_pid=$!
ledger_session_cleanup() {
  kill "$ledger_window_manager_pid" 2>/dev/null || true
  wait "$ledger_window_manager_pid" 2>/dev/null || true
}
trap ledger_session_cleanup EXIT
trap 'ledger_session_record 130; exit 130' INT
trap 'ledger_session_record 143; exit 143' TERM
trap 'ledger_session_record 129; exit 129' HUP
export ARC_LEDGER_FULLSCREEN=1 ARC_LEDGER_XSESSION=1
ledger_status=0
bash "$ledger_program/START_OFFICE.sh" || ledger_status=$?
ledger_session_record "$ledger_status"
exit "$ledger_status"
