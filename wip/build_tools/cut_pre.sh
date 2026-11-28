#!/bin/bash
# cut_pre.sh COMMIT OUT [BASE_KIT]: cut a Graphite 1.1 preview kit from COMMIT.
# It reuses the Debian 13 packages of an earlier kit (default: the last kit sent, $S/work/r114/kit), so no chroot and no
# network are needed: the earlier kit is joined, Graphite's own four packages in it are replaced by ones built from
# COMMIT, the folder repository is indexed again, and the kit is packed (every file under 15,000,000 bytes).
# Use a fresh chroot build (tools/build_repo.sh) instead when a slice changes what Graphite's packages depend on.
set -euo pipefail
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
PY=$S/work/venv/bin/python; COMMIT=$1; OUT=$2; BASE=${3:-$S/work/r114/kit}          # the last kit sent (Kas 1.1.4)
[ -f "$BASE/PIECES.sha256" ] || { echo "no earlier kit in $BASE"; exit 2; }
case "$BASE/" in "$OUT"/*) echo "OUT ($OUT) holds the base kit ($BASE): choose another OUT"; exit 2;; esac
rm -rf "$OUT"; mkdir -p "$OUT/src" "$OUT/debs"
git -C /home/user/Struthio archive "$COMMIT" | tar -x -C "$OUT/src"
cd "$OUT/src"
V=$($PY -B tools/debian_pkg.py version); echo "commit $COMMIT, Debian version $V"
# the seed, the registry and the manifest must already match the commit (merge_one.sh rebuilds them): check only
QT_QPA_PLATFORM=offscreen $PY -B tools/record_registry.py --check >"$OUT/registry_check.txt" 2>&1 || { echo "registry check FAILED"; tail -5 "$OUT/registry_check.txt"; exit 3; }
PYTHONDONTWRITEBYTECODE=1 PYTHON=$PY bash tools/build_deb.sh --out "$OUT/debs" --work "$OUT/stage"
rm -rf "$OUT/stage"
# the earlier kit, joined into $OUT/base/repo and checked
$PY -B - "$OUT/src/tools" "$BASE" "$OUT/base" <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import debian_pkg
problems = debian_pkg.join(sys.argv[2], sys.argv[3])
if problems: raise SystemExit('the earlier kit does not check: %s' % problems[:5])
print('earlier kit joined and checked')
PY
R=$OUT/base/repo
gone=0; dest=""
for p in kas-computer kas-llama-runtime kas-session kas-desktop graphite graphite-llama-runtime graphite-session graphite-desktop; do
  for old in $(find "$R" -name "${p}_*.deb"); do echo "replacing $(basename "$old")"; dest=$(dirname "$old"); rm -f "$old"; gone=$((gone+1)); done
done
[ "$gone" -ge 4 ] || { echo "expected at least 4 of our packages in the earlier kit, found $gone"; exit 4; }
cp "$OUT"/debs/*.deb "$dest/"
n=$($PY -B "$OUT/src/tools/debian_pkg.py" index "$R" --label 'Graphite kit')
{ echo; echo "Preview cut $(date -u +%F): Graphite's four packages rebuilt as $V from commit $COMMIT; the Debian 13 packages are the earlier kit's."; } >> "$R/CLOSURE.txt"
echo "repository: $n packages"
PYTHON=$PY bash "$OUT/src/tools/build_kit.sh" --repo "$R" --out "$OUT/kit"
rm -rf "$OUT/base"
(cd "$OUT/kit" && sha256sum * > "$OUT/SHA256SUMS.kit")
ls -la "$OUT/kit" | awk 'NR>1{print $5, $9}' | tail -4; echo "kit files: $(ls "$OUT/kit" | wc -l)"
