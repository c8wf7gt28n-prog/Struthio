#!/usr/bin/env bash
# Orchestrator's release cut: export one commit of the Graphite branch, package it with the project's own tools, split it
# into parts, restore the parts with the project's installer, check the restored tree, and assemble the start-here bundle.
# usage: cut.sh COMMIT OUTDIR
set -euo pipefail
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
PY=$S/work/venv/bin/python; COMMIT=$1; OUT=$2; OLD=$S/x/Graphite_00_START_HERE/Graphite_Transfer
rm -rf "$OUT"; mkdir -p "$OUT/src" "$OUT/full" "$OUT/Graphite_Transfer/App"
git -C /home/user/Struthio archive "$COMMIT" | tar -x -C "$OUT/src"
cd "$OUT/src"
SHORT=$($PY -B -c "import sys;sys.path.insert(0,'.');from workbench.version import SHORT;print(SHORT)")
QT_QPA_PLATFORM=offscreen $PY -B tools/package_graphite.py "$OUT/full" > "$OUT/package.json"
QT_QPA_PLATFORM=offscreen $PY -B tools/package_release_parts.py "$OUT/full/Graphite_${SHORT}_full.zip" "$OUT/Graphite_Transfer/App" "Graphite $SHORT" > "$OUT/parts.json"
cd "$OUT/Graphite_Transfer/App"
sha256sum Graphite_${SHORT}_part_*.zip > SHA256SUMS
cp "$OUT/src/INSTALL_LS.py" . ; cp "$OUT/src/INSTALL_LS.py" ..
cp "$OUT/src/PREPARE_DEBIAN.sh" . ; cp "$OLD/App/OFFLINE_FILES.json" "$OLD/App/DEBIAN_USB.sha256" .
sed "s/Graphite-0\.2a13/Graphite-$SHORT/" "$OLD/App/INSTALL_GRAPHITE.sh" > INSTALL_GRAPHITE.sh
grep -q "Graphite-$SHORT" INSTALL_GRAPHITE.sh
head -1 DEBIAN_USB.sha256 | sha256sum --check --quiet -          # the offline inventory still names this OFFLINE_FILES.json
cp "$S/work/kit_START_HERE.md" ../START_HERE.md
# restore with the project's installer and check what came out
cd "$OUT/Graphite_Transfer"; rm -rf "$OUT/Restored"
$PY -B INSTALL_LS.py --usb App --target "$OUT/Restored" --offline --extract-only | tail -1
diff -rq "$OUT/src" "$OUT/Restored" && echo "restored tree is identical to commit $COMMIT"
(cd "$OUT/Restored" && QT_QPA_PLATFORM=offscreen $PY -B tools/check_release.py 2>/dev/null) > "$OUT/release_check_restored.json"
python3 -I -c "
import json;r=json.load(open('$OUT/release_check_restored.json'));print('release check on the restored tree:',r['state'],'| files',r['runtime']['payload']['files'],'|',r['release']['title'])"
# the bundle: everything in Graphite_Transfer except the numbered parts
cd "$OUT"; mkdir -p deliver; cp Graphite_Transfer/App/Graphite_${SHORT}_part_*.zip deliver/
(cd "$OUT" && zip -q -r "deliver/Graphite_${SHORT}_START_HERE.zip" Graphite_Transfer -x "Graphite_Transfer/App/Graphite_${SHORT}_part_*.zip")
ls -la deliver | awk '{print $5, $9}'; awk '$1>=15000000{bad=1} END{exit bad}' <(stat -c %s deliver/*.zip) && echo "every ZIP is under 15,000,000 bytes"
unzip -l "deliver/Graphite_${SHORT}_START_HERE.zip" | tail -12
