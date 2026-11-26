#!/usr/bin/env bash
# The dedicated session's supervisor (Graphite 1.0 S1, the session that survives). Private session client: Debian login
# files and other desktops stay untouched.
#
# For the whole session it keeps the D-Bus session (dbus-run-session, below) and Fluxbox (started again if it ends), and it
# runs Graphite's window (START_OFFICE.sh) as its child:
#   - Graphite ends with status 0 (Return to Debian, or the ordinary close after Log out, Restart or Shut down asked the
#     system): the session ends;
#   - Graphite asked to be started again (a hand-over request in the session folder, workbench/session_launch.py) and ended
#     with status 0: it is started again at once with the settings asked for (another workspace or look); nothing else ends;
#   - any other end (an error status, a crash, killed): Graphite is started again after a wait that grows (2 s, 4 s, 8 s,
#     at most 30 s), at most ARC_LEDGER_SESSION_RESTART_LIMIT times in a row (3 unless set; a run of two minutes or more starts
#     the count afresh); after that the session ends at the text console, where START_MINIMAL_DEBIAN.sh prints the plain
#     message recorded here.
# Program windows opened from Graphite run in sessions of their own (session_launch.launch), so they stay open while Graphite
# is started again; they close only when the session ends, with the X server.
# The final status is recorded in ${XDG_STATE_HOME:-$HOME/.local/state}/ledger-slate/last-session.json (xinit discards the
# client's status) with how many times Graphite was started again and, when the session could not be kept running, the
# message; each start and end is one line in session.log beside it. Nothing here logs out, suspends or powers off.
set -uo pipefail
ledger_program="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${DISPLAY:-}" ]]; then echo 'Use START_MINIMAL_DEBIAN.sh from a text login.' >&2; exit 1; fi
if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
  exec dbus-run-session -- bash "$ledger_program/LS_XSESSION.sh"
fi
ledger_state_dir="${XDG_STATE_HOME:-${HOME:-}/.local/state}/ledger-slate"
ledger_session_marker="$ledger_state_dir/.session-start"
ledger_number() { # $1 if it is a whole number from 0 to $3, else $2
  if [[ "$1" =~ ^[0-9]{1,4}$ ]] && (( 10#$1 <= $3 )); then echo $(( 10#$1 )); else echo "$2"; fi
}
ledger_limit="$(ledger_number "${ARC_LEDGER_SESSION_RESTART_LIMIT:-}" 3 20)"     # starts again in a row, at most
ledger_backoff="$(ledger_number "${ARC_LEDGER_SESSION_BACKOFF:-}" 2 60)"          # the first wait, in seconds (doubled each time)
ledger_stable="$(ledger_number "${ARC_LEDGER_SESSION_STABLE:-}" 120 3600)"       # a run this long (seconds) starts the count afresh
ledger_json() { local text="$1"; text="${text//\\/\\\\}"; text="${text//\"/\\\"}"; printf '"%s"' "$text"; }
ledger_log_line() { # one line in session.log; a failure to write changes nothing
  {
    local log="$ledger_state_dir/session.log"
    if [[ -f "$log" ]] && (( $(stat -c %s -- "$log" 2>/dev/null || echo 0) > 262144 )); then mv -f -- "$log" "$log.1"; fi
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$log"
  } 2>/dev/null || true
}
ledger_error_log() { # the launch error log written during this session (not older than the start marker), or nothing
  local candidate
  for candidate in "$ledger_state_dir/launch-error.log" "$(dirname -- "$ledger_program")/launch-error.log"; do
    if [[ -f "$candidate" ]] && ! [[ "$candidate" -ot "$ledger_session_marker" ]]; then printf '%s' "$candidate"; return 0; fi
  done
  return 1
}
ledger_session_record() {
  # Write {"status","utc","log","restarts","message"}; a failure to write never changes the exit status.
  {
    local status="$1" restarts="${2:-0}" message="${3:-}" log json_log='null' json_message='null'
    log="$(ledger_error_log)" && json_log="$(ledger_json "$log")"
    if [[ -n "$message" ]]; then json_message="$(ledger_json "$message")"; fi
    printf '{"status":%d,"utc":"%s","log":%s,"restarts":%d,"message":%s}\n' "$status" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$json_log" "$restarts" "$json_message" > "$ledger_state_dir/last-session.json.tmp" \
      && mv -f "$ledger_state_dir/last-session.json.tmp" "$ledger_state_dir/last-session.json"
  } 2>/dev/null || true
}
{ mkdir -p "$ledger_state_dir" && : > "$ledger_session_marker"; } 2>/dev/null || true

# The session folder (private): the hand-over request and the record of the programs Graphite started.
if [[ -n "${XDG_RUNTIME_DIR:-}" && -d "${XDG_RUNTIME_DIR:-}" && -w "${XDG_RUNTIME_DIR:-}" ]]; then ledger_session_dir="$XDG_RUNTIME_DIR/graphite-xsession"
else ledger_session_dir="$ledger_state_dir/xsession"; fi
if { mkdir -p -m 700 -- "$ledger_session_dir" && chmod 700 -- "$ledger_session_dir"; } 2>/dev/null; then
  rm -f -- "$ledger_session_dir/next-start" "$ledger_session_dir/programs.jsonl" 2>/dev/null
  export ARC_LEDGER_SESSION_DIR="$ledger_session_dir"
else
  ledger_session_dir=''; unset ARC_LEDGER_SESSION_DIR
fi

# Fluxbox, hidden, for the whole session (started again if it ends, at most five times).
ledger_window_manager_pid=''
ledger_window_manager_starts=0
ledger_start_window_manager() {
  fluxbox -no-slit -no-toolbar &
  ledger_window_manager_pid=$!; ledger_window_manager_starts=$(( ledger_window_manager_starts + 1 ))
}
ledger_graphite_pid=''
ledger_pause_pid=''
ledger_ending=''
ledger_session_cleanup() {
  if [[ -n "$ledger_pause_pid" ]]; then kill "$ledger_pause_pid" 2>/dev/null || true; fi
  if [[ -n "$ledger_window_manager_pid" ]]; then
    kill "$ledger_window_manager_pid" 2>/dev/null || true
    wait "$ledger_window_manager_pid" 2>/dev/null || true
  fi
  if [[ -n "$ledger_session_dir" ]]; then rm -f -- "$ledger_session_dir/next-start" 2>/dev/null || true; fi
}
ledger_signal() { # the session is being ended from outside (logind, the X server going, a signal): Graphite is asked to end
  ledger_ending="$1"
  if [[ -n "$ledger_pause_pid" ]]; then kill "$ledger_pause_pid" 2>/dev/null || true; fi
  if [[ -n "$ledger_graphite_pid" ]]; then kill -TERM "$ledger_graphite_pid" 2>/dev/null || true; fi
}
trap ledger_session_cleanup EXIT
trap 'ledger_signal 130' INT
trap 'ledger_signal 143' TERM
trap 'ledger_signal 129' HUP
ledger_end_by_signal() { # Graphite had five seconds to end after the signal; then the session ends with the signal's status
  local waited=0
  while [[ -n "$ledger_graphite_pid" ]] && kill -0 "$ledger_graphite_pid" 2>/dev/null && (( waited < 50 )); do sleep 0.1; waited=$(( waited + 1 )); done
  ledger_log_line "the session was ended from outside (status $ledger_ending)"
  ledger_session_record "$ledger_ending" "$ledger_restarts"
  exit "$ledger_ending"
}
ledger_wait_graphite() { # waits for Graphite, starting Fluxbox again if it ends meanwhile; returns Graphite's status
  local ended status
  while :; do
    if [[ -n "$ledger_ending" ]]; then return 0; fi
    if [[ -n "$ledger_window_manager_pid" ]] && (( BASH_VERSINFO[0] > 5 || (BASH_VERSINFO[0] == 5 && BASH_VERSINFO[1] >= 1) )); then
      ended=''
      wait -n -p ended "$ledger_graphite_pid" "$ledger_window_manager_pid"; status=$?
      # a trapped signal ends the wait with no job, and bash then unsets the -p variable
      if [[ "${ended:-}" == "$ledger_graphite_pid" ]]; then return "$status"; fi
      if [[ -n "${ended:-}" && "${ended:-}" == "$ledger_window_manager_pid" ]]; then
        if (( ledger_window_manager_starts < 6 )); then
          ledger_log_line "Fluxbox ended (status $status); starting it again"; ledger_start_window_manager
        else
          ledger_log_line "Fluxbox ended (status $status) again; the session goes on without it"; ledger_window_manager_pid=''
        fi
      fi
    else
      wait "$ledger_graphite_pid"; status=$?
      if ! kill -0 "$ledger_graphite_pid" 2>/dev/null; then return "$status"; fi
    fi
  done
}
ledger_handed=()
ledger_read_hand_over() { # the hand-over request (NUL-separated +NAME=value and -NAME entries), only Graphite's own settings
  local file="$ledger_session_dir/next-start" entry name
  local -a sets=() unsets=()
  [[ -n "$ledger_session_dir" && -f "$file" ]] || return 1
  while IFS= read -r -d '' entry; do
    case "$entry" in
      +*=*) name="${entry:1}"; name="${name%%=*}";;
      -*) name="${entry:1}";;
      *) continue;;
    esac
    [[ "$name" =~ ^(ARC_LEDGER_|ARC1_|GRAPHITE_)[A-Z0-9_]*$ ]] || continue
    case "$name" in ARC_LEDGER_XSESSION|ARC_LEDGER_FULLSCREEN|ARC_LEDGER_SESSION_*) continue;; esac
    if [[ "$entry" == +* ]]; then sets+=("${entry:1}"); else unsets+=(-u "$name"); fi
  done < "$file"
  rm -f -- "$file"
  ledger_handed=("${unsets[@]}" "${sets[@]}")
  return 0
}

export ARC_LEDGER_FULLSCREEN=1 ARC_LEDGER_XSESSION=1
ledger_start_window_manager
ledger_restarts=0
ledger_failures=0
ledger_status=0
ledger_message=''
while :; do
  export ARC_LEDGER_SESSION_RESTARTS="$ledger_restarts" ARC_LEDGER_SESSION_LAST_STATUS="$ledger_status"
  ledger_started=$SECONDS
  env "${ledger_handed[@]}" bash "$ledger_program/START_OFFICE.sh" &
  ledger_graphite_pid=$!
  ledger_log_line "Graphite started (process $ledger_graphite_pid)"
  ledger_wait_graphite; ledger_status=$?
  if [[ -n "$ledger_ending" ]]; then ledger_end_by_signal; fi
  ledger_ran=$(( SECONDS - ledger_started ))
  ledger_log_line "Graphite ended with status $ledger_status after $ledger_ran s"
  if ledger_read_hand_over && (( ledger_status == 0 )); then
    ledger_failures=0; ledger_log_line "Graphite asked to be started again with other settings"; continue
  fi
  if (( ledger_status == 0 )); then break; fi
  if (( ledger_ran >= ledger_stable )); then ledger_failures=0; fi
  ledger_failures=$(( ledger_failures + 1 ))
  if (( ledger_failures > ledger_limit )); then
    ledger_details="$(ledger_error_log)" || ledger_details=''
    ledger_message="Graphite ended unexpectedly ${ledger_failures} times in a row (last status ${ledger_status}), so the session ended here at the text console instead of starting it again. Apps that were open closed with the session.${ledger_details:+ Details: ${ledger_details}.} To start again: bash ${ledger_program}/START_MINIMAL_DEBIAN.sh. To look for the cause first: bash ${ledger_program}/START_OFFICE.sh --doctor"
    ledger_log_line "giving up: $ledger_message"
    echo "$ledger_message" >&2
    break
  fi
  ledger_pause=$(( ledger_backoff << (ledger_failures - 1) )); if (( ledger_pause > 30 )); then ledger_pause=30; fi
  ledger_restarts=$(( ledger_restarts + 1 ))
  ledger_log_line "starting Graphite again in $ledger_pause s ($ledger_failures of $ledger_limit in a row)"
  sleep "$ledger_pause" & ledger_pause_pid=$!
  wait "$ledger_pause_pid" 2>/dev/null; ledger_pause_pid=''
  if [[ -n "$ledger_ending" ]]; then ledger_end_by_signal; fi
done
ledger_session_record "$ledger_status" "$ledger_restarts" "$ledger_message"
exit "$ledger_status"
