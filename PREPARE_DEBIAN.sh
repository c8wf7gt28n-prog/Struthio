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

# 1.0 R1: give apt only the files that move this system forward. The set only grows (the 1.0 packages sit beside the
# 0.8.x ones), so a package already installed here at the same or a newer version (a system kept up to date) is left as
# it is, and a package the set holds twice is taken at its newer version.
declare -A newest_file=() newest_version=() newest_query=()
for deb in "${packages[@]}"; do
    fields=$(dpkg-deb --show --showformat='${Package} ${Version} ${Architecture}' "$deb") || fail "Debian could not read ${deb##*/}."
    read -r name version arch <<< "$fields"
    if [[ -z ${newest_version[$name]:-} ]] || dpkg --compare-versions "$version" gt "${newest_version[$name]}"; then
        newest_file[$name]=$deb
        newest_version[$name]=$version
        newest_query[$name]=$name
        [[ $arch == all ]] || newest_query[$name]=$name:$arch
    fi
done
install=()
current=0
for name in "${!newest_file[@]}"; do
    installed=$(dpkg-query --show --showformat='${db:Status-Abbrev}${Version}' "${newest_query[$name]}" 2>/dev/null || true)
    if [[ $installed =~ ^.i\ (.+)$ ]] && dpkg --compare-versions "${BASH_REMATCH[1]}" ge "${newest_version[$name]}"; then
        current=$((current + 1))
    else
        install+=("${newest_file[$name]}")
    fi
done
if [[ ${#install[@]} -gt 0 ]]; then mapfile -t install < <(printf '%s\n' "${install[@]}" | LC_ALL=C sort); fi

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
# 1.0 R1: say what is left as it is, and stop early when nothing is new
printf '%s are already installed at the same or a newer version and stay as they are; %s to give to apt.\n' "$current" "${#install[@]}"
if [[ ${#install[@]} -eq 0 ]]; then
    printf '%s\n' 'Nothing to install: every package of this set is already here. Continue from your ordinary user account.'
    exit 0
fi
if [[ $# -eq 1 ]]; then
    # 1.0 R1: when the plan does not resolve, show apt's reasons (they are on its standard output)
    plan=$(LC_ALL=C apt-get "${apt_options[@]}" -s install "${install[@]}") || {
        printf '%s\n' "$plan" | sed -n '/unmet dependencies/,$p' >&2
        fail 'The offline package plan does not resolve on this computer; apt says why above. Nothing was changed.'
    }
    printf '%s\n' "$plan" | awk '/ upgraded, .* newly installed, / {print}'
    printf '%s\n' 'Offline package plan resolved. Run the same script without --plan to install.'
else
    apt-get "${apt_options[@]}" -y install "${install[@]}"
    # 1.0 R1: the session services of the 1.0 set (logind's session, sound) start at the next login
    printf '%s\n' 'Verified offline Debian packages installed. Log out and log in again, then continue from your ordinary user account.'
fi
