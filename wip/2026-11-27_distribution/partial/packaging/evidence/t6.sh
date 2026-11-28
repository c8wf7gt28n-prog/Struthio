#!/bin/bash
plist() { for p in /proc/[0-9]*; do u=$(stat -c %U $p 2>/dev/null); [ "$u" = tester ] && echo "$(basename $p) $(tr '\0' ' ' < $p/cmdline | cut -c1-110)"; done; }
echo "### (d) the session supervisor from the packaged location (stand-in fluxbox, no X: offscreen)"
mkdir -p /tmp/stub /tmp/xrt; printf '#!/bin/sh\nexec sleep 100000\n' > /tmp/stub/fluxbox; chmod +x /tmp/stub/fluxbox; chown tester /tmp/xrt; chmod 700 /tmp/xrt
rm -rf /home/tester/.local/state/ledger-slate
runuser -u tester -- env -i HOME=/home/tester PATH=/tmp/stub:/usr/bin:/bin LC_ALL=C.UTF-8 XDG_RUNTIME_DIR=/tmp/xrt QT_QPA_PLATFORM=offscreen DISPLAY=:99 DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/xrt/nobus /bin/bash /usr/lib/graphite/LS_XSESSION.sh > /root/session.out 2>&1 &
sleep 35
echo "-- session.log:"; cat /home/tester/.local/state/ledger-slate/session.log 2>&1 | cut -c1-200
echo "-- processes:"; plist
sup=$(plist | awk '/LS_XSESSION/{print $1}' | head -1); kill -TERM $sup; sleep 9
echo "-- last-session.json:"; cat /home/tester/.local/state/ledger-slate/last-session.json 2>&1; echo "-- left running:"; plist; for p in $(plist | cut -d' ' -f1); do kill -KILL $p 2>/dev/null; done
echo "-- supervisor output (tail):"; tail -4 /root/session.out | cut -c1-300
echo "### (f) a signed apt repository in a folder (the USB stick layout), used with every network source disabled"
install -m 644 /debs/graphite-archive-keyring.gpg /usr/share/keyrings/graphite-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/graphite-archive-keyring.gpg] file:/debs ./" > /etc/apt/sources.list.d/graphite.list
apt-get update -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/graphite.list -o Dir::Etc::sourceparts=/nonexistent 2>&1 | tail -4
apt-cache policy graphite graphite-session | grep -E "^[a-z]|Candidate|file:" | cut -c1-120
echo "-- unsigned variant is refused by apt 3.0:"; mkdir -p /tmp/unsigned && cp /debs/Packages /debs/Release /tmp/unsigned/ && echo "deb file:/tmp/unsigned ./" > /tmp/u.list && apt-get update -o Dir::Etc::sourcelist=/tmp/u.list -o Dir::Etc::sourceparts=/nonexistent -o Dir::State::lists=/tmp/ulists 2>&1 | grep -E "^(E|W|N):" | head -3 | cut -c1-200
echo "### (e) remove and purge: what stays"
ls -d /home/tester/Concern/Office /home/tester/.config/arc1-workbench 2>&1
apt-get remove -y graphite 2>&1 | grep -E "Removing|warning|not empty|upgraded" | cut -c1-200
echo "-- /usr/lib/graphite after remove:"; ls /usr/lib/graphite 2>&1 | head -5; find /usr/lib/graphite -type f 2>/dev/null | wc -l
echo "-- the user's workspace and profile after remove:"; ls -d /home/tester/Concern/Office /home/tester/.config/arc1-workbench /home/tester/.local/state/ledger-slate 2>&1; du -sk /home/tester | cut -f1
apt-get autoremove --purge -s 2>&1 | grep -E "upgraded" 
