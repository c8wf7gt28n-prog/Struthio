#!/usr/bin/env bash
# 1.1 PK1: pack the folder repository (tools/build_repo.sh) as the kit the owner receives.
#   tools/build_kit.sh --repo REPO --out KIT
# Every file in KIT is smaller than 15,000,000 bytes: the repository goes into GRAPHITE_NNN.zip files; a file larger
# than one ZIP is cut into pieces (each in its own ZIP) that JOIN.sh puts together again, every piece and every whole
# file checked by sha256 (PIECES.sha256, SHA256SUMS). Beside them: START_HERE.md, JOIN.sh, install.sh and KIT.sha256.
set -euo pipefail
tree="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
repo=''; kit=''
while [[ $# -gt 0 ]]; do
  case "$1" in --repo) repo="$2"; shift 2 ;; --out) kit="$2"; shift 2 ;; *) echo "Unknown option: $1" >&2; exit 2 ;; esac
done
[[ -f "$repo/Packages" && -n "$kit" ]] || { echo 'Needs --repo REPO (with Packages) and --out KIT.' >&2; exit 2; }
python="${PYTHON:-python3}"
version="$("$python" "$tree/tools/debian_pkg.py" version)"
mkdir -p "$kit"
"$python" "$tree/tools/debian_pkg.py" pack "$repo" "$kit"
for name in JOIN.sh install.sh; do install -m 755 "$tree/debian/kit/$name" "$kit/$name"; done
sed "s/@VERSION@/$version/g" "$tree/debian/kit/START_HERE.md" > "$kit/START_HERE.md"
( cd "$kit" && sha256sum START_HERE.md JOIN.sh install.sh PIECES.sha256 SHA256SUMS GRAPHITE_*.zip > KIT.sha256 )
"$python" - "$kit" <<'PY'
import sys, pathlib
files = [p for p in pathlib.Path(sys.argv[1]).iterdir() if p.is_file()]
big = [p.name for p in files if p.stat().st_size >= 15_000_000]
if big: raise SystemExit('Files too large for the kit: %s' % big)
print('kit: %d files, %d bytes, the largest %d bytes (all under 15,000,000)' % (
    len(files), sum(p.stat().st_size for p in files), max(p.stat().st_size for p in files)))
PY
