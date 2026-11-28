#!/bin/bash
mkdir -p /tmp/x && cd /tmp/x && dpkg-deb --fsys-tarfile /debs/graphite_1.0-1_all.deb | tar -x ./usr/lib/graphite/INSTALL_DEBIAN.sh ./usr/lib/graphite/INSTALL_LEDGER.sh ./usr/lib/graphite/START_MINIMAL_DEBIAN.sh ./usr/lib/graphite/PREPARE_DEBIAN.sh && chmod -R a+rX /tmp/x
id tester >/dev/null 2>&1 || useradd -m tester
echo "### (i) the online path on a Debian without sudo (root password set at install): INSTALL_DEBIAN.sh --quick --yes --minimal-session, as the ordinary user"
runuser -u tester -- env -i HOME=/home/tester PATH=/usr/bin:/bin bash /tmp/x/usr/lib/graphite/INSTALL_DEBIAN.sh --quick --yes --minimal-session 2>&1 | tail -3 | cut -c1-260; echo "rc=${PIPESTATUS[0]}"
echo "### (i2) the same as root"
env -i HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin bash /tmp/x/usr/lib/graphite/INSTALL_DEBIAN.sh --quick --yes --minimal-session 2>&1 | tail -2 | cut -c1-260; echo "rc=${PIPESTATUS[0]}"
echo "### (j) START_MINIMAL_DEBIAN.sh from a text login without the session packages"
runuser -u tester -- env -i HOME=/home/tester PATH=/usr/bin:/bin bash /tmp/x/usr/lib/graphite/START_MINIMAL_DEBIAN.sh 2>&1 | tail -2 | cut -c1-260
echo "### (k) PREPARE_DEBIAN.sh on Debian 13.8 with no kit beside it"
bash /tmp/x/usr/lib/graphite/PREPARE_DEBIAN.sh --plan 2>&1 | tail -2 | cut -c1-260
