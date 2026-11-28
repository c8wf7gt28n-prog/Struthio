#!/usr/bin/env bash
# 1.1 PK1: make the kit's folder repository: Graphite's packages and the Debian 13 packages they need, downloaded in a
# clean Debian 13 chroot, resolved against a computer that already has the Graphite 1.0 System set.
#   tools/build_repo.sh --debs DIR --out REPO --keyring debian-archive-keyring.gpg [options]   (as root)
# Options:
#   --against STATUS   dpkg status of the computer the kit is for (default debian/kit/system-set-1.0.status)
#   --work DIR         where the chroot is made (default: a new folder under /tmp; put it on tmpfs to spare the disk)
#   --mirror URL       Debian mirror (default https://deb.debian.org/debian; security from https://security.debian.org)
#   --cainfo FILE      a CA bundle apt inside the chroot needs for https (a proxy's), copied in
#   --sign-with KEYID  sign Release (InRelease, Release.gpg) and export the key as graphite-archive-keyring.gpg;
#                      without it the repository is unsigned and install.sh marks the folder source trusted, checked by
#                      checksums (previews; the release key is the owner's to make and keep)
#   --keep-chroot      leave the chroot (with the System set installed) in WORK/chroot for an install test
# What it does: debootstrap --variant=minbase trixie (the debootstrap and keyring files are fetched from the mirror and
# checked against its signed index when debootstrap is not installed); installs the packages the System set's status
# lists; then downloads, with Recommends, what `apt-get install graphite graphite-session graphite-llama-runtime
# graphite-desktop` needs twice: against that chroot, and against the System set's status (its exact versions). The
# repository is flat (Packages, Packages.xz, Release) and CLOSURE.txt says what came in and why.
set -euo pipefail
tree="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
debs=''; out=''; keyring=''; against="$tree/debian/kit/system-set-1.0.status"; work=''; mirror='https://deb.debian.org/debian'
security='https://security.debian.org/debian-security'; cainfo=''; sign=''; keep=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --debs) debs="$2"; shift 2 ;; --out) out="$2"; shift 2 ;; --keyring) keyring="$2"; shift 2 ;;
    --against) against="$2"; shift 2 ;; --work) work="$2"; shift 2 ;; --mirror) mirror="$2"; shift 2 ;;
    --cainfo) cainfo="$2"; shift 2 ;; --sign-with) sign="$2"; shift 2 ;; --keep-chroot) keep=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ "$EUID" == 0 ]] || { echo 'build_repo.sh makes a chroot: run it as root.' >&2; exit 1; }
[[ -d "$debs" && -n "$out" && -f "$keyring" && -f "$against" ]] || { echo 'Needs --debs DIR, --out REPO, --keyring FILE (and a status file).' >&2; exit 2; }
python="${PYTHON:-python3}"; helper="$tree/tools/debian_pkg.py"
debs="$(cd "$debs" && pwd)"; keyring="$(cd "$(dirname "$keyring")" && pwd)/$(basename "$keyring")"
[[ -n "$work" ]] || work="$(mktemp -d)"; mkdir -p "$work" "$out"; work="$(cd "$work" && pwd)"; out="$(cd "$out" && pwd)"
root="$work/chroot"; log="$work/build_repo.log"; : > "$log"
say() { echo "[build_repo] $*" | tee -a "$log"; }

# ---- debootstrap (fetched and checked when it is not installed)
bootstrap="$(command -v debootstrap || true)"
if [[ -z "$bootstrap" ]]; then
  say 'fetching debootstrap from the signed trixie index'
  mkdir -p "$work/fetch" && cd "$work/fetch"
  curl -fsS -o InRelease "$mirror/dists/trixie/InRelease"
  gpgv --keyring "$keyring" InRelease >>"$log" 2>&1 || { say 'InRelease signature NOT valid'; exit 1; }
  curl -fsS -o Packages.xz "$mirror/dists/trixie/main/binary-amd64/Packages.xz"
  "$python" - "$mirror" <<'PY' >>"$log"
import hashlib, lzma, re, sys, urllib.request, subprocess
mirror = sys.argv[1]
rel = open('InRelease').read()
want = re.search(r'^ ([0-9a-f]{64}) +\d+ main/binary-amd64/Packages.xz$', rel.split('SHA256:', 1)[1], re.M).group(1)
data = open('Packages.xz', 'rb').read()
assert hashlib.sha256(data).hexdigest() == want, 'Packages.xz does not match the signed InRelease'
for para in lzma.decompress(data).decode().split('\n\n'):
    name = re.search(r'^Package: (\S+)$', para, re.M)
    if name and name.group(1) == 'debootstrap':
        path = re.search(r'^Filename: (\S+)$', para, re.M).group(1); digest = re.search(r'^SHA256: (\S+)$', para, re.M).group(1)
        subprocess.run(['curl', '-fsS', '-o', 'debootstrap.deb', mirror + '/' + path], check=True)
        assert hashlib.sha256(open('debootstrap.deb', 'rb').read()).hexdigest() == digest, 'debootstrap.deb changed'
        print('debootstrap', path, 'sha256 OK'); break
else:
    raise SystemExit('debootstrap not in the index')
PY
  dpkg-deb -x debootstrap.deb "$work/debootstrap"
  export DEBOOTSTRAP_DIR="$work/debootstrap/usr/share/debootstrap"; bootstrap="$work/debootstrap/usr/sbin/debootstrap"
  cd "$work"
fi
command -v wget >/dev/null || { say 'debootstrap needs wget on this host'; exit 1; }

inroot() { # run a command inside the chroot, in private mount and process namespaces (the mounts end with it)
  unshare --mount --pid --fork --kill-child bash -c '
    r="$1"; shift; mount -t proc proc "$r/proc"; mount --rbind /dev "$r/dev"; mount -t tmpfs tmpfs "$r/run"; mount -t tmpfs tmpfs "$r/tmp"
    mkdir -p "$r/graphite-debs"; mount --bind "$GRAPHITE_DEBS" "$r/graphite-debs"
    exec chroot "$r" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive \
      https_proxy="${https_proxy:-}" http_proxy="${http_proxy:-}" "$@"' inroot "$root" "$@"
}
export GRAPHITE_DEBS="$debs"

# ---- the clean Debian 13 chroot
rm -rf -- "$root"
say "debootstrap --variant=minbase trixie into $root"
"$bootstrap" --variant=minbase --components=main,non-free-firmware --keyring="$keyring" trixie "$root" "$mirror" >>"$log" 2>&1
cat > "$root/etc/apt/sources.list" <<EOF
deb $mirror trixie main non-free-firmware
deb $mirror trixie-updates main non-free-firmware
deb $security trixie-security main non-free-firmware
EOF
printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"; chmod 755 "$root/usr/sbin/policy-rc.d"
{ echo 'Acquire::Languages "none";'; echo 'APT::Install-Suggests "false";'
  if [[ -n "$cainfo" ]]; then cp "$cainfo" "$root/etc/ssl/graphite-build-ca.crt"; echo 'Acquire::https::CAInfo "/etc/ssl/graphite-build-ca.crt";'; fi
} > "$root/etc/apt/apt.conf.d/90graphite-build"
grep -v '^#' "$against" > "$root/root/system-set.status"
"$python" - "$root/root/system-set.status" > "$root/root/system-set.names" <<'PY'
import re, sys
print('\n'.join(sorted({m for m in re.findall(r'^Package: (\S+)$', open(sys.argv[1]).read(), re.M)})))
PY
say "installing the System set's $(wc -l < "$root/root/system-set.names") packages"
inroot sh -c 'apt-get update -q && xargs -a /root/system-set.names apt-get install -y -q --no-install-recommends' >>"$log" 2>&1
inroot apt-get clean

# ---- Graphite's own packages as a folder source inside the chroot
"$python" "$helper" index "$debs" --label 'Graphite packages' >/dev/null
echo 'deb [trusted=yes] file:/graphite-debs ./' > "$root/etc/apt/sources.list.d/graphite-debs.list"
inroot apt-get update -q >>"$log" 2>&1
wanted='graphite graphite-session graphite-llama-runtime graphite-desktop'
say 'downloading the closure against the chroot (System set installed, today'"'"'s versions)'
mkdir -p "$root/var/cache/graphite-a/partial" "$root/var/cache/graphite-b/partial"
inroot sh -c "apt-get install -s -o APT::Install-Recommends=true $wanted > /root/plan-chroot.txt && apt-get install -y -q --download-only -o APT::Install-Recommends=true -o Dir::Cache::archives=/var/cache/graphite-a $wanted" >>"$log" 2>&1
say 'downloading the closure against the System set status (its exact versions)'
inroot sh -c "apt-get install -s -o Dir::State::status=/root/system-set.status -o APT::Install-Recommends=true $wanted > /root/plan-status.txt && apt-get install -y -q --download-only -o Dir::State::status=/root/system-set.status -o APT::Install-Recommends=true -o Dir::Cache::archives=/var/cache/graphite-b $wanted" >>"$log" 2>&1

# ---- the repository
find "$out" -maxdepth 1 -name '*.deb' -delete
cp -n "$debs"/*.deb "$out"/
for cache in graphite-a graphite-b; do find "$root/var/cache/$cache" -maxdepth 1 -name '*.deb' -exec cp -n {} "$out"/ \; ; done
count="$("$python" "$helper" index "$out" --label 'Graphite kit')"
{ echo "Graphite kit repository: $count packages, $(du -sm "$out" | cut -f1) MB"; echo
  echo "== against the chroot with the System set installed (today's versions):"; grep -E '^(Inst|[0-9]+ upgraded)' "$root/root/plan-chroot.txt" || true; echo
  echo "== against the System set status (its exact versions):"; grep -E '^(Inst|[0-9]+ upgraded)' "$root/root/plan-status.txt" || true
} > "$out/CLOSURE.txt"
if [[ -n "$sign" ]]; then
  gpg --batch --yes --local-user "$sign" --clearsign -o "$out/InRelease" "$out/Release"
  gpg --batch --yes --local-user "$sign" -abs -o "$out/Release.gpg" "$out/Release"
  gpg --batch --yes --export "$sign" > "$out/graphite-archive-keyring.gpg"
  say "signed with $sign"
else
  rm -f "$out/InRelease" "$out/Release.gpg" "$out/graphite-archive-keyring.gpg"
fi
say "repository: $out ($count packages)"
if [[ "$keep" == 0 ]]; then rm -rf -- "$root"; say 'chroot removed'; fi
