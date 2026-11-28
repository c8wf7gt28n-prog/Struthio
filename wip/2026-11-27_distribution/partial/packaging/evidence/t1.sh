#!/bin/bash
# run as root in the chroot; drops to the ordinary user "tester" for every program run
id tester >/dev/null 2>&1 || useradd -m -s /bin/bash tester
touch /root/marker; sleep 1
run() { runuser -u tester -- env -i HOME=/home/tester PATH=/usr/bin:/bin LC_ALL=C.UTF-8 XDG_RUNTIME_DIR=/tmp/xrt QT_QPA_PLATFORM=offscreen "$@"; }
mkdir -p /tmp/xrt && chown tester /tmp/xrt && chmod 700 /tmp/xrt
cd /
echo "### T1 graphite --version"; run graphite --version; echo "rc=$?"
echo "### T1b from another cwd (/home/tester)"; ( cd /home/tester && run graphite --version ); echo "rc=$?"
echo "### T2 graphite --doctor (tail)"; run timeout 300 graphite --doctor > /root/doctor.out 2>&1; echo "rc=$?"; python3 - <<'PY'
import json,re
t=open('/root/doctor.out').read()
try:
    d=json.loads(t[t.index('{'):])
    for k in ('state','version'): print(k, d.get(k))
    for k in ('payload','foundation'):
        v=d.get(k) or (d.get('checks') or {}).get(k)
        if isinstance(v,dict): print(k, v.get('state'), (v.get('problems') or [])[:3])
    print('dependencies', d.get('dependencies'))
    print('keys', list(d)[:25])
except Exception as e:
    print('not json:', e); print(t[-1500:])
PY
echo "### T3 offscreen start: graphite --check"; ( time run timeout 420 graphite --check ) > /root/check.out 2>&1; echo "rc=$?"; tail -15 /root/check.out | cut -c1-300
echo "### T4 payload verify + seed status after py3compile"; run python3 -c "
import sys; sys.path.insert(0,'/usr/lib/graphite')
from pathlib import Path
from workbench.release_integrity import verify
from workbench.stacy_foundation import seed_status
r=verify(Path('/usr/lib/graphite')); print('payload',r['state'],r['files'],r['problems'][:3])
s=seed_status(Path('/usr/lib/graphite')); print('seed',s['state'])"
echo "### T8 anything written under /usr/lib/graphite since marker?"; find /usr/lib/graphite -newer /root/marker | head; echo "(end)"
echo "### T8b what the user's home got"; find /home/tester -maxdepth 3 -newer /root/marker | head -30
