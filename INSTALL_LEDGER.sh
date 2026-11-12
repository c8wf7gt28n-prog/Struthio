#!/usr/bin/env bash
# Runtime only. No models, engineering tools, source changes, or workspace migration.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
wheelhouse=""
check_only=0
math_tools=0
experiment_tools=0
quick=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --offline) [[ $# -ge 2 ]] || { echo 'Supply the wheel folder after --offline.' >&2; exit 1; }; wheelhouse="$2"; shift 2 ;;
    --check-only) check_only=1; shift ;;
    --quick) quick=1; shift ;;
    --math) math_tools=1; shift ;;
    --experiments) experiment_tools=1; shift ;;
    --help|-h)
      echo 'Usage: bash INSTALL_LEDGER.sh [--math] [--experiments] [--check-only] [--quick] [--offline WHEEL_FOLDER]'
      echo 'Creates or reuses .venv; --math also installs pinned math and document dependencies.'
      echo '--experiments adds the pinned Wasmtime binding for bundled, qualified WASI Python experiments.'
      echo '--quick checks runtime imports and package/source integrity; extended walkthroughs remain available separately.'
      echo 'Offline mode never falls back to downloading. Supply wheels for this Python and platform.'
      exit 0 ;;
    *) echo "Unknown installation option: $1" >&2; exit 1 ;;
  esac
done
ledger_python="${LEDGER_PYTHON:-python3}"
command -v "$ledger_python" >/dev/null || { echo 'Install Python 3.11-3.13 first.' >&2; exit 1; }
"$ledger_python" -c 'import sys; raise SystemExit(0 if (3,11)<=sys.version_info[:2]<(3,14) else "Python 3.11-3.13 is required")'
"$ledger_python" -c 'from pathlib import Path; from workbench.release_integrity import verify; r=verify(Path.cwd()); print("Package:", r["state"]); raise SystemExit(0 if r["state"]=="VERIFIED" else str(r["problems"][:5]))'
if [[ "$check_only" == 1 ]]; then exec "$ledger_python" -m workbench.doctor; fi
if [[ "$EUID" == 0 ]]; then
  echo 'Run the Graphite installer as your ordinary desktop user. Use INSTALL_DEBIAN.sh for sudo prerequisites.' >&2; exit 1
fi
if [[ -n "$wheelhouse" && ! -d "$wheelhouse" ]]; then echo 'The offline wheel folder does not exist.' >&2; exit 1; fi
if [[ ! -x .venv/bin/python ]]; then
  "$ledger_python" -m venv .venv || { echo 'Install python3-venv, then run this command again.' >&2; exit 1; }
fi
.venv/bin/python -c 'import sys; raise SystemExit(0 if (3,11)<=sys.version_info[:2]<(3,14) else "This .venv uses an unsupported Python. Keep it aside and create a new environment.")'
ledger_requirements=(-r requirements-qt.txt)
if [[ "$math_tools" == 1 ]]; then ledger_requirements+=(-r requirements-math.txt -r requirements-office.txt); fi
if [[ "$experiment_tools" == 1 ]]; then ledger_requirements+=(-r requirements-experiments.txt); fi
if [[ -n "$wheelhouse" ]]; then
  .venv/bin/python -m pip --isolated --disable-pip-version-check install --only-binary=:all: --no-index --find-links "$wheelhouse" "${ledger_requirements[@]}"
else
  .venv/bin/python -m pip --disable-pip-version-check install "${ledger_requirements[@]}"
fi
if [[ "$quick" == 1 ]]; then
  .venv/bin/python -c 'from pathlib import Path; from PySide6.QtWidgets import QApplication; from PySide6.QtSvg import QSvgRenderer; import cryptography, pypdf; from workbench.release_integrity import verify; from workbench.stacy_foundation import seed_status; root=Path.cwd(); assert verify(root)["state"]=="VERIFIED"; assert seed_status(root)["state"]=="VERIFIED_SOURCE_BINDINGS"; print("Runtime imports, package and source bindings verified. Owner display and native/model qualification remain separate.")'
  echo 'Start the Office: bash START_OFFICE.sh'
  ledger_missing=()
  for ledger_command in startx fluxbox dbus-run-session; do command -v "$ledger_command" >/dev/null || ledger_missing+=("$ledger_command"); done
  command -v Xorg >/dev/null || command -v X >/dev/null || ledger_missing+=(Xorg)
  if [[ ${#ledger_missing[@]} -eq 0 ]]; then
    echo 'Minimal Debian session: bash START_MINIMAL_DEBIAN.sh'
  else
    echo "Minimal session prerequisites not found: ${ledger_missing[*]} (bash INSTALL_DEBIAN.sh --minimal-session --quick --yes installs them; from an existing desktop START_MINIMAL_DEBIAN.sh still opens the fullscreen Office)"
  fi
  exit 0
fi
ledger_report=".venv/baseline-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.doctor --self-test --json >"$ledger_report"; then
  echo "Installation needs attention. Read $ledger_report or run: bash LEDGER.sh doctor --self-test" >&2; exit 2
fi
ledger_desk_report=".venv/project-desk-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.project_desk_checks >"$ledger_desk_report"; then
  echo "Project Desk needs attention. Read $ledger_desk_report" >&2; exit 2
fi
ledger_context_report=".venv/slate-context-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.slate_checks >"$ledger_context_report"; then
  echo "Graphite context needs attention. Read $ledger_context_report" >&2; exit 2
fi
ledger_edit_report=".venv/changes-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.edit_checks >"$ledger_edit_report"; then
  echo "Change recovery needs attention. Read $ledger_edit_report" >&2; exit 2
fi
ledger_work_report=".venv/continuing-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.continuing_checks >"$ledger_work_report"; then
  echo "Continuing work needs attention. Read $ledger_work_report" >&2; exit 2
fi
ledger_exchange_report=".venv/exchange-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.deployment_checks >"$ledger_exchange_report"; then
  echo "Paired exchange needs attention. Read $ledger_exchange_report" >&2; exit 2
fi
ledger_update_report=".venv/updates-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
if ! .venv/bin/python -m workbench.update_checks >"$ledger_update_report"; then
  echo "Signed update recovery needs attention. Read $ledger_update_report" >&2; exit 2
fi
echo 'Runtime installed. Six stages of disposable walkthroughs passed, including paired exchange and signed update recovery. Owner display, physical appliances, protected workers and real-model trials remain separate.'
echo 'Start the Office: bash START_OFFICE.sh'
echo 'Check the real Qt window: bash LEDGER.sh doctor --qt-check'
echo "Report: $ledger_report"

if [[ "$math_tools" == 1 ]]; then
  .venv/bin/python -m workbench.math_checks --no-office
  echo "Math adapters checked. Run python3 -m workbench.math_checks for the actual Calc and Writer round trip."
fi
