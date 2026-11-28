#!/bin/bash
# run a command inside the Debian 13 chroot, in private mount+pid namespaces (mounts vanish with the process)
export CW=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/dist/packaging
exec nice -n 19 unshare --mount --pid --fork --kill-child bash -c '
  C=$CW/chroot
  mount -t proc proc $C/proc; mount --rbind /dev $C/dev; mount -t tmpfs tmpfs $C/run; mount -t tmpfs tmpfs $C/tmp
  mount --bind $CW/debs $C/debs
  exec chroot $C /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root TERM=dumb LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive https_proxy="$https_proxy" "$@"' inchroot "$@"
