#!/usr/bin/env bash
# The 1.0 release cut (R2). As cut.sh for 0.8.7, with three differences: the install metadata comes from the 1.0 System
# set (wip/build_tools/kit_1.0: OFFLINE_FILES.json and DEBIAN_USB.sha256 with 540 entries, INSTALL_GRAPHITE.sh), the 136
# new Debian packages travel in ZIPs of their own (Graphite_1.0_system_add_part_NN.zip, each under 15,000,000 bytes,
# rooted at Graphite_Transfer/App/debs/ beside the 0.8.x debs), and the start page is the 1.0 one.
# usage: cut_1.0.sh COMMIT OUTDIR
set -euo pipefail
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
PY=$S/work/venv/bin/python; COMMIT=$1; OUT=$2; KIT=/home/user/Struthio/wip/build_tools/kit_1.0
DEBS=$S/work/b100/R1/debs_new; START=/home/user/Struthio/wip/build_tools/kit_START_HERE_1.0.md
[ -d "$DEBS" ] || { echo "the 1.0 debs are not in $DEBS: re-fetch them from $KIT/SYSTEM_SET_1.0.json first"; exit 2; }
rm -rf "$OUT"; mkdir -p "$OUT/src" "$OUT/full" "$OUT/Graphite_Transfer/App"
git -C /home/user/Struthio archive "$COMMIT" | tar -x -C "$OUT/src"
cd "$OUT/src"
SHORT=$($PY -B -c "import sys;sys.path.insert(0,'.');from workbench.version import SHORT;print(SHORT)")
QT_QPA_PLATFORM=offscreen $PY -B tools/package_graphite.py "$OUT/full" > "$OUT/package.json"
QT_QPA_PLATFORM=offscreen $PY -B tools/package_release_parts.py "$OUT/full/Graphite_${SHORT}_full.zip" "$OUT/Graphite_Transfer/App" "Graphite $SHORT" > "$OUT/parts.json"
cd "$OUT/Graphite_Transfer/App"
sha256sum Graphite_${SHORT}_part_*.zip > SHA256SUMS
cp "$OUT/src/INSTALL_LS.py" . ; cp "$OUT/src/INSTALL_LS.py" ..
cp "$OUT/src/PREPARE_DEBIAN.sh" . ; cp "$KIT/OFFLINE_FILES.json" "$KIT/DEBIAN_USB.sha256" .
sed "s/Graphite-0\.2a13/Graphite-$SHORT/" "$KIT/INSTALL_GRAPHITE.sh" > INSTALL_GRAPHITE.sh
grep -q "Graphite-$SHORT" INSTALL_GRAPHITE.sh
head -1 DEBIAN_USB.sha256 | sha256sum --check --quiet -          # the inventory names this OFFLINE_FILES.json
# the 1.0 debs: each one must be in the inventory with its checksum
mkdir -p debs; cp "$DEBS"/*.deb debs/
n=$(ls debs/*.deb | wc -l); echo "1.0 debs: $n"
grep -E '  debs/' DEBIAN_USB.sha256 | while read -r sum name; do [ -f "$name" ] && echo "$sum  $name"; done > ../debs_new.sha256
[ "$(wc -l < ../debs_new.sha256)" -eq "$n" ] || { echo "a 1.0 deb is missing from the inventory"; exit 3; }
sha256sum --check --strict --quiet ../debs_new.sha256 && echo "every 1.0 deb matches the inventory"
cp "$START" ../START_HERE.md
cp "$KIT/WHAT_THE_1.0_SYSTEM_SET_ADDS.md" "$KIT/SYSTEM_SET_1.0.json" ..
# restore with the project's installer and check what came out
cd "$OUT/Graphite_Transfer"; rm -rf "$OUT/Restored"
$PY -B INSTALL_LS.py --usb App --target "$OUT/Restored" --offline --extract-only | tail -1
diff -rq "$OUT/src" "$OUT/Restored" && echo "restored tree is identical to commit $COMMIT" || true
(cd "$OUT/Restored" && QT_QPA_PLATFORM=offscreen $PY -B tools/check_release.py 2>/dev/null) > "$OUT/release_check_restored.json" || true
python3 -I -c "
import json;r=json.load(open('$OUT/release_check_restored.json'));print('release check on the restored tree:',r['state'],'| files',r['runtime']['payload']['files'],'|',r['release']['title'])"
# the deliverable: the numbered application parts, the system additions in ZIPs under the limit, and the START_HERE ZIP
cd "$OUT"; mkdir -p deliver; cp Graphite_Transfer/App/Graphite_${SHORT}_part_*.zip deliver/
python3 -I - "$OUT" "$SHORT" <<'PYZ'
import sys, zipfile, os
out, short = sys.argv[1], sys.argv[2]
debs = sorted(os.listdir(os.path.join(out, 'Graphite_Transfer/App/debs')))
LIMIT = 14_000_000; part = 1; size = 0; z = None
def new():
    global z, part, size
    if z: z.close(); part += 1
    z = zipfile.ZipFile(os.path.join(out, 'deliver', 'Graphite_%s_system_add_part_%02d.zip' % (short, part)), 'w', zipfile.ZIP_STORED)
    size = 0
new()
for d in debs:
    p = os.path.join(out, 'Graphite_Transfer/App/debs', d); s = os.path.getsize(p)
    if size and size + s > LIMIT: new()
    z.write(p, 'Graphite_Transfer/App/debs/' + d); size += s
z.close(); print('system additions:', part, 'ZIPs for', len(debs), 'debs')
PYZ
(cd "$OUT" && zip -q -r "deliver/Graphite_${SHORT}_START_HERE.zip" Graphite_Transfer -x "Graphite_Transfer/App/Graphite_${SHORT}_part_*.zip" -x "Graphite_Transfer/App/debs/*" -x "Graphite_Transfer/debs_new.sha256")
(cd deliver && sha256sum *.zip > ../SHA256SUMS.kit)
ls -la deliver | awk '{print $5, $9}'; awk '$1>=15000000{bad=1} END{exit bad}' <(stat -c %s deliver/*.zip) && echo "every ZIP is under 15,000,000 bytes"
unzip -l "deliver/Graphite_${SHORT}_START_HERE.zip" | tail -14
