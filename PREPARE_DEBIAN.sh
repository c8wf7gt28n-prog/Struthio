#!/usr/bin/env bash
# Install the Debian USB cache on a text-only system, including Python when needed.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

fail() { printf '%s\n' "$1" >&2; exit 1; }
[[ $# -eq 0 || ( $# -eq 1 && $1 == --plan ) ]] || fail 'Usage: bash PREPARE_DEBIAN.sh [--plan]'
if [[ $# -eq 0 && $EUID -ne 0 ]]; then fail 'Run this Debian package step from the root console.'; fi
[[ -r /etc/debian_version ]] || fail 'This USB cache requires Debian 13 amd64.'
IFS=. read -r debian_version _ < /etc/debian_version
[[ $debian_version == 13 && $(dpkg --print-architecture) == amd64 ]] || fail 'This USB cache requires Debian 13 amd64.'

inventory=DEBIAN_USB.sha256
[[ -f $inventory ]] || fail 'Put this script, DEBIAN_USB.sha256, and both extracted dependency archives in the same USB directory.'
packages=()
wheels=0
manifest=0
while read -r digest member; do
    [[ $digest =~ ^[0-9a-f]{64}$ ]] || fail 'The USB checksum list is invalid.'
    if [[ $member =~ ^debs/[^/[:space:]]+\.deb$ ]]; then
        packages+=("$PWD/$member")
    elif [[ $member =~ ^wheels/[^/[:space:]]+\.whl$ ]]; then
        ((wheels+=1))
    elif [[ $member == OFFLINE_FILES.json ]]; then
        manifest=1
    else
        fail 'The USB checksum list names an unexpected file.'
    fi
done < "$inventory"
[[ ${#packages[@]} -gt 0 && $wheels -gt 0 && $manifest -eq 1 ]] || fail 'The USB dependency checksum list is incomplete.'
sha256sum --check --strict --quiet -- "$inventory" || fail 'The USB dependency files did not match. Re-extract both dependency archives.'

empty_sources=$(mktemp -d)
trap 'rm -rf -- "$empty_sources"' EXIT
mkdir -p "$empty_sources/sources.list.d" "$empty_sources/lists"
: > "$empty_sources/sources.list"
apt_options=(
    -o "Dir::Etc::sourcelist=$empty_sources/sources.list"
    -o "Dir::Etc::sourceparts=$empty_sources/sources.list.d"
    -o "Dir::State::lists=$empty_sources/lists"
    --no-remove --no-install-recommends
)
printf 'Verified %s Debian packages and %s Python wheels for Debian 13 amd64.\n' "${#packages[@]}" "$wheels"
if [[ $# -eq 1 ]]; then
    plan=$(LC_ALL=C apt-get "${apt_options[@]}" -s install "${packages[@]}")
    printf '%s\n' "$plan" | awk '/ upgraded, .* newly installed, / {print}'
    printf '%s\n' 'Offline package plan resolved. Run the same script without --plan to install.'
else
    apt-get "${apt_options[@]}" -y install "${packages[@]}"
    printf '%s\n' 'Verified offline Debian packages installed. Continue from your ordinary user account.'
fi
