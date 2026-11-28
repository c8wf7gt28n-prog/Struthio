#!/bin/bash
set -o pipefail
echo "== join the 1.1.6 kit $(date -u +%H:%M)"
/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python -B - <<'PYJ' || exit 11
import sys; sys.path.insert(0, '/home/user/Struthio/tools'); import debian_pkg
p = debian_pkg.join('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/r116/kit', '/dev/shm/it/kit')
print('joined:', 'ok' if not p else p[:3])
PYJ
cp /dev/shm/it/kit/repo/kas-*.deb /dev/shm/it/kit/repo/graphite*.deb /dev/shm/it/debs/ && ls /dev/shm/it/debs
echo "== chroot with the 1.0 System set $(date -u +%H:%M)"
cd /home/user/Struthio && PYTHON=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python bash tools/build_repo.sh --debs /dev/shm/it/debs --out /dev/shm/it/repo2 --keyring /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b100/R1/keyring/debian/x/usr/share/keyrings/debian-archive-keyring.gpg --work /dev/shm/it/work --cainfo /root/.ccr/ca-bundle.crt --keep-chroot 2>&1 | grep -v 'warning: behavior of -n' | tail -5 || exit 12
R=/dev/shm/it/work/chroot; [ -d $R/usr ] || { echo "no chroot"; exit 13; }
echo "== install kas from the kit's repository, as install.sh does $(date -u +%H:%M)"
mkdir -p $R/var/lib/kas-test && cp -r /dev/shm/it/kit/repo $R/var/lib/kas-test/repo
echo 'deb [trusted=yes] file:/var/lib/kas-test/repo ./' > $R/etc/apt/sources.list.d/kas-test.list
for d in proc sys dev; do mount --bind /$d $R/$d 2>/dev/null || true; done
chroot $R /bin/sh -c 'apt-get update -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/kas-test.list -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0 >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/kas-test.list -o Dir::Etc::sourceparts=- kas-computer kas-session 2>&1 | tail -4'
echo "== what is installed $(date -u +%H:%M)"
chroot $R /bin/sh -c 'dpkg -l "kas-*" "graphite*" 2>/dev/null | grep "^ii" | awk "{print \$2, \$3}"; for c in kas-startx kas-session kas-do kas-doctor kas-computer graphite-startx; do printf "%s: " $c; command -v $c || echo MISSING; done'
echo "== kas-computer --version"; chroot $R /bin/sh -c 'QT_QPA_PLATFORM=offscreen timeout 60 kas-computer --version 2>&1 | tail -2'
echo "== graphite-startx (the old name) says"; chroot $R /bin/sh -c 'timeout 10 graphite-startx --help 2>&1 | head -3'
echo "== kas-doctor doctor"; chroot $R /bin/sh -c 'QT_QPA_PLATFORM=offscreen timeout 120 kas-doctor doctor 2>&1 | tail -6'
for d in dev sys proc; do umount $R/$d 2>/dev/null || true; done
echo "== done $(date -u +%H:%M)"
