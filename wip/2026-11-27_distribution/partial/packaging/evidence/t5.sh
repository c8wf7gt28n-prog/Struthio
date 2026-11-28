#!/bin/bash
echo "### (d) the session supervisor from the packaged location (stand-in fluxbox, no X: offscreen)"
mkdir -p /tmp/stub /tmp/xrt; printf '#!/bin/sh\nexec sleep 100000\n' > /tmp/stub/fluxbox; chmod +x /tmp/stub/fluxbox; chown tester /tmp/xrt; chmod 700 /tmp/xrt
runuser -u tester -- env -i HOME=/home/tester PATH=/tmp/stub:/usr/bin:/bin LC_ALL=C.UTF-8 XDG_RUNTIME_DIR=/tmp/xrt QT_QPA_PLATFORM=offscreen DISPLAY=:99 DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/xrt/nobus graphite-session > /root/session.out 2>&1 &
sup=$!; sleep 30
echo "-- session.log:"; cat /home/tester/.local/state/ledger-slate/session.log 2>&1 | cut -c1-200
echo "-- processes:"; ps -eo user,pid,ppid,etime,args | grep -E "LS_XSESSION|workbench.launch|fluxbox" | grep -v grep | cut -c1-150
pkill -TERM -u tester -f LS_XSESSION.sh; sleep 9
echo "-- last-session.json:"; cat /home/tester/.local/state/ledger-slate/last-session.json 2>&1; echo "-- left running:"; ps -eo user,args | grep -E "^tester" | cut -c1-120; pkill -KILL -u tester 2>/dev/null
echo "-- supervisor output (tail):"; tail -5 /root/session.out | cut -c1-300
echo "### (f) a signed apt repository in a folder (the USB stick layout), used offline"
apt-get install -y apt-utils 2>&1 | grep -E "newly installed"; apt-get clean
cd /debs && apt-ftparchive -o APT::FTPArchive::Release::Origin=Graphite -o APT::FTPArchive::Release::Label=Graphite -o APT::FTPArchive::Release::Suite=stable -o APT::FTPArchive::Release::Codename=graphite release . > /tmp/Release && mv /tmp/Release Release && head -6 Release
