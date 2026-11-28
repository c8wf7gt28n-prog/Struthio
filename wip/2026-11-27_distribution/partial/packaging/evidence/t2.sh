#!/bin/bash
run() { runuser -u tester -- env -i HOME=/home/tester PATH=/usr/bin:/bin LC_ALL=C.UTF-8 XDG_RUNTIME_DIR=/tmp/xrt QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 "$@"; }
mkdir -p /tmp/xrt && chown tester /tmp/xrt && chmod 700 /tmp/xrt
cd /usr/lib/graphite
for m in "$@"; do
  echo "### unittest $m"; ( time run timeout 900 python3 -B -m unittest tests_integrated.$m ) > /root/ut_$m.out 2>&1; echo "rc=$?"; tail -6 /root/ut_$m.out | cut -c1-400
done
