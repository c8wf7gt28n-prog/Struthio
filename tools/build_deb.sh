#!/usr/bin/env bash
# 1.1 PK1: build Kas's Debian packages from this tree with dpkg-deb (no debhelper needed). 1.1 R1: the four kas-*
# packages and the four transitional graphite* ones (debian/control).
#   tools/build_deb.sh [--out DIR] [--work DIR]
# Gives graphite_<v>_all.deb (the program in /usr/lib/graphite, /usr/bin/graphite, the desktop entry and icon),
# graphite-llama-runtime_<v>_amd64.deb (the bundled llama.cpp archives), graphite-session_<v>_all.deb (the X session
# entry, graphite-session and graphite-startx) and graphite-desktop_<v>_all.deb (the LightDM metapackage).
# The version comes from workbench/version.py. The payload is exactly what MANIFEST.json lists, so rebuild the seed and
# the manifest first after any change (tools/package_graphite.py --manifest-only; tools/record_registry.py;
# tools/package_graphite.py --manifest-only).
set -euo pipefail
tree="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
out="$tree/build/debian"; work=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) out="$2"; shift 2 ;;
    --work) work="$2"; shift 2 ;;
    *) echo "Unknown option: $1 (use --out DIR, --work DIR)" >&2; exit 2 ;;
  esac
done
command -v dpkg-deb >/dev/null || { echo 'dpkg-deb is needed (Debian: apt install dpkg).' >&2; exit 1; }
python="${PYTHON:-python3}"
version="$("$python" "$tree/tools/debian_pkg.py" version)"
[[ -n "$work" ]] || work="$(mktemp -d)"
mkdir -p "$out" "$work"
for package in kas-computer kas-llama-runtime kas-session kas-desktop graphite graphite-llama-runtime graphite-session graphite-desktop; do
  stage="$work/$package"
  "$python" - "$tree" "$package" "$stage" <<'PY'
import sys; sys.path.insert(0, sys.argv[1] + '/tools')
import debian_pkg
print('%s: %d files staged' % (sys.argv[2], debian_pkg.stage(sys.argv[2], sys.argv[3], root=debian_pkg.Path(sys.argv[1]))))
PY
  arch="$(sed -n 's/^Architecture: //p' "$stage/DEBIAN/control")"
  deb="$out/${package}_${version}_${arch}.deb"
  rm -f -- "$deb"
  dpkg-deb --root-owner-group -Zxz --build "$stage" "$deb" >/dev/null
  echo "built $deb ($(stat -c %s "$deb") bytes)"
  rm -rf -- "$stage"
done
