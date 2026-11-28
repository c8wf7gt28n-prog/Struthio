#!/usr/bin/env bash
# 1.1 PK1: install Graphite from the kit's folder repository with apt. Run as root (su -), after bash JOIN.sh:
#   bash install.sh --check      show what apt would do; changes nothing
#   bash install.sh              stage 1: graphite and graphite-session (start with graphite-startx, as before)
#   bash install.sh --desktop    stage 2, optional: graphite-desktop, the graphical login (LightDM)
#   bash install.sh --forget     remove the kit's apt source and its copy (installed packages stay)
# The repository is copied to /var/lib/graphite-kit/repo and added as an apt source. A preview kit is not signed: the
# source is marked trusted and every file is checked by sha256 (SHA256SUMS here, and apt checks each package against
# Packages). A signed kit carries graphite-archive-keyring.gpg and is used with Signed-By instead.
set -euo pipefail
kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:-install}"
place=/var/lib/graphite-kit/repo; list=/etc/apt/sources.list.d/graphite-kit.list; key=/usr/share/keyrings/graphite-archive-keyring.gpg
[[ "$EUID" == 0 ]] || { echo 'Run install.sh as root: su -   then   bash '"$kit"'/install.sh' >&2; exit 1; }
if [[ "$mode" == --forget ]]; then
  rm -f -- "$list" "$key"; rm -rf -- /var/lib/graphite-kit
  echo 'The kit source is gone. Installed packages stay; apt remove takes them away.'; exit 0
fi
case "$mode" in install|--check|--desktop) ;; *) echo "Unknown option: $mode (use --check, --desktop or --forget)" >&2; exit 2 ;; esac
. /etc/os-release
[[ "${ID:-}" == debian && "${VERSION_ID:-}" == 13 ]] || { echo "This kit is for Debian 13; this is ${PRETTY_NAME:-unknown}." >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == amd64 ]] || { echo 'This kit is for amd64 computers.' >&2; exit 1; }
[[ -f "$kit/repo/Packages" ]] || { echo 'No repository yet: run   bash JOIN.sh   in the kit folder first (as your user).' >&2; exit 1; }
echo 'Checking every file of the repository (sha256)...'
( cd "$kit/repo" && sha256sum --quiet -c "$kit/SHA256SUMS" ) || { echo 'A file does not match SHA256SUMS. Copy the kit again.' >&2; exit 1; }
if [[ "$kit/repo" != "$place" ]]; then
  rm -rf -- "$place.new"; mkdir -p "$(dirname "$place")"; cp -r -- "$kit/repo" "$place.new"
  rm -rf -- "$place"; mv -- "$place.new" "$place"
fi
chmod -R a+rX /var/lib/graphite-kit
if [[ -f "$place/graphite-archive-keyring.gpg" && -f "$place/InRelease" ]]; then
  install -m 644 "$place/graphite-archive-keyring.gpg" "$key"
  echo "deb [signed-by=$key] file:$place ./" > "$list"
else
  echo "deb [trusted=yes] file:$place ./" > "$list"
fi
apt-get update -o Dir::Etc::sourcelist="$list" -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0
packages='graphite graphite-session'
[[ "$mode" == --desktop ]] && packages='graphite-desktop'
if [[ "$mode" == --check ]]; then
  apt-get install -s $packages | grep -E '^(Inst|Conf|Remv|[0-9]+ upgraded|E:)' || true
  echo 'Nothing was changed (--check).'; exit 0
fi
apt-get install -y $packages
if [[ "$mode" == --desktop ]]; then
  echo 'Installed graphite-desktop. At the next boot the login screen offers the Graphite session.'
  echo 'To go back to the text console:  systemctl disable lightdm   (then reboot; graphite-startx still works there)'
  echo 'To remove the login screen:      apt remove graphite-desktop lightdm lightdm-gtk-greeter'
else
  echo 'Installed graphite and graphite-session. Log out of root, log in as your user on the text console and type:'
  echo '  graphite-startx'
fi
