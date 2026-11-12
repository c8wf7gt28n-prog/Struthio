#!/usr/bin/env bash
# Debian entry point: optional apt prerequisites (sudo, only after --yes or a
# terminal answer), then INSTALL_LEDGER.sh for the runtime.
# Exit status: 0 = runtime installer succeeded and any requested apt packages were
# installed; 3 = runtime installer succeeded but the apt packages were SKIPPED
# (no --yes and no terminal, or declined at the prompt) - the line
# PREREQUISITES_SKIPPED is printed so INSTALL_LS.py and people can read it back;
# any other status comes from the runtime installer or an apt failure.
# --offline and --check-only run no apt command and do not count as skipped.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
engineering=0
workers=0
math_tools=0
experiment_tools=0
assume_yes=0
skip_apt=0
apt_skipped=''
minimal_session=0
network_capture=0
vulkan=0
calc=0
forward=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --engineering) engineering=1; shift ;;
    --workers) workers=1; shift ;;
    --math) math_tools=1; forward+=("$1"); shift ;;
    --experiments) experiment_tools=1; forward+=("$1"); shift ;;
    --yes) assume_yes=1; shift ;;
    --minimal-session) minimal_session=1; shift ;;
    --network-capture) network_capture=1; shift ;;
    --vulkan) vulkan=1; shift ;;
    --calc) calc=1; shift ;;
    --quick) forward+=("$1"); shift ;;
    --check-only) skip_apt=1; forward+=("$1"); shift ;;
    --offline) [[ $# -ge 2 ]] || { echo 'Supply a wheel folder.' >&2; exit 1; }; skip_apt=1; forward+=("$1" "$2"); shift 2 ;;
    --help|-h) echo 'Usage: bash INSTALL_DEBIAN.sh [--yes] [--engineering] [--workers] [--math] [--experiments] [--minimal-session] [--network-capture] [--vulkan] [--calc] [--quick] [--check-only | --offline WHEELS]'; echo 'Only --engineering adds compilers, Git, Node, Icarus and clangd. --workers adds bubblewrap and user-service prerequisites, without qualifying a profile. --network-capture adds wireshark-common (dumpcap) for the packet capture in Log, Network; it never changes groups. --vulkan adds maintained Debian Vulkan/Radeon packages, with no repository, group or kernel changes. Enable Debian non-free-firmware separately if firmware-amd-graphics is unavailable. Offline/check modes run no apt commands.'; echo '--calc adds LibreOffice Calc. With an offline cache, supply its matching Debian dependencies in the cache.'; echo 'Exit 3 with the line PREREQUISITES_SKIPPED means the runtime installer succeeded but the apt packages were skipped (no --yes and no terminal, or declined).'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done
if [[ ! -f /etc/debian_version ]] || ! command -v apt-get >/dev/null; then
  echo 'Use INSTALL_LEDGER.sh on a non-Debian system.' >&2; exit 1
fi
if [[ "$skip_apt" == 0 ]]; then
  packages=(python3 python3-venv python3-pip libgl1 libegl1 libfontconfig1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 libxcb-xinerama0 poppler-utils)
  if [[ "$engineering" == 1 ]]; then packages+=(build-essential git nodejs iverilog clangd); fi
  if [[ "$math_tools" == 1 ]]; then packages+=(libreoffice-calc libreoffice-writer default-jdk-headless)
  elif [[ "$calc" == 1 ]]; then packages+=(libreoffice-calc); fi
  if [[ "$experiment_tools" == 1 ]]; then packages+=(kicad); fi
  if [[ "$workers" == 1 ]]; then packages+=(bubblewrap dbus-user-session libpam-systemd); fi
  if [[ "$minimal_session" == 1 ]]; then packages+=(xserver-xorg xinit fluxbox x11-xserver-utils xauth dbus-x11 fonts-dejavu-core network-manager libgl1-mesa-dri); fi
  if [[ "$network_capture" == 1 ]]; then packages+=(wireshark-common); fi  # dumpcap for the optional packet capture (docs/NETWORK_01.md)
  if [[ "$vulkan" == 1 ]]; then packages+=(libvulkan1 mesa-vulkan-drivers firmware-amd-graphics vulkan-tools libstdc++6 libgomp1 libssl3t64 zlib1g libzstd1 libgcc-s1 libc6); fi
  echo "Prerequisites: ${packages[*]}"
  answer=n
  if [[ "$assume_yes" == 1 ]]; then answer=y; elif [[ -t 0 ]]; then read -r -p 'Install these prerequisites using sudo? [y/N] ' answer; apt_skipped='declined at the prompt'; else apt_skipped='no --yes and no terminal for the sudo prompt'; fi
  if [[ "$answer" == y || "$answer" == Y ]]; then
    apt_skipped=''
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends "${packages[@]}"
  else
    echo "System packages skipped ($apt_skipped). The runtime installer will use installed prerequisites."
  fi
fi
# network-capture steps: begin
if [[ "$network_capture" == 1 ]]; then
  # Explained, never done here: capture without the administrator is the owner's own choice (docs/NETWORK_01.md). The steps
  # are word for word those Log's Network stream lists (workbench/network_watch.py: RECONFIGURE, join_step, RELOG).
  login="$(id -un 2>/dev/null || true)"
  [[ "$login" =~ ^[a-z_][a-z0-9_.-]{0,31}\$?$ ]] || login='<your login>'
  echo 'Packet capture (optional): dumpcap captures without the administrator only when non-superuser capture was allowed and'
  echo 'you are in the wireshark group. If the package did not ask, or you answered No:'
  echo '  as the administrator, dpkg-reconfigure wireshark-common, and answer Yes: non-superusers may capture packets'
  echo "  as the administrator, usermod -aG wireshark $login"
  echo '  log out and in again, so the session carries the wireshark group'
  echo 'This installer does not run them, and Graphite never runs them and never changes the system’s permissions.'
fi
# network-capture steps: end
ledger_rc=0
bash ./INSTALL_LEDGER.sh "${forward[@]}" || ledger_rc=$?
if [[ "$ledger_rc" == 0 && -n "$apt_skipped" ]]; then
  echo "PREREQUISITES_SKIPPED: the Debian packages listed above were not installed ($apt_skipped); the runtime checks passed with what is already installed. Re-run with --yes to install them."
  exit 3
fi
exit "$ledger_rc"
