#!/bin/bash
apt-get autoremove --purge -y >/dev/null 2>&1; apt-get purge -y gnupg apt-utils >/dev/null 2>&1; apt-get autoremove --purge -y >/dev/null 2>&1; apt-get clean; echo "packages now: $(dpkg -l | grep -c '^ii')"
echo "### (g) ISO assembly tools, really installed and run"
apt-get install -y --no-install-recommends squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin grub-common mtools 2>&1 | grep -E "newly installed|^E:"; apt-get clean
mkdir -p /tmp/iso/boot/grub /tmp/iso/live /tmp/rootfs && cp -a /usr/share/doc /tmp/rootfs/ && echo "Graphite live image stand-in" > /tmp/rootfs/README
( time mksquashfs /tmp/rootfs /tmp/iso/live/filesystem.squashfs -comp xz -noappend -quiet ) 2>&1 | grep -E "real|rror"; ls -l /tmp/iso/live/filesystem.squashfs | awk '{print "squashfs bytes:", $5}'; unsquashfs -l /tmp/iso/live/filesystem.squashfs | tail -1
cat > /tmp/iso/boot/grub/grub.cfg <<'G'
serial --unit=0 --speed=115200
terminal_input serial console
terminal_output serial console
echo GRAPHITE_ISO_SMOKE_OK
ls (cd0)/live/
sleep 1
halt
G
grub-mkrescue -o /tmp/t.iso /tmp/iso > /tmp/mkrescue.log 2>&1; echo "grub-mkrescue rc=$?"; tail -2 /tmp/mkrescue.log | cut -c1-200; ls -l /tmp/t.iso | awk '{print "iso bytes:", $5}'; xorriso -indev /tmp/t.iso -report_el_torito plain 2>/dev/null | grep -E "El Torito boot img|platform" | head -6
echo "### (h) QEMU without KVM (TCG): boot the ISO to GRUB on the serial line"
apt-get install -y --no-install-recommends qemu-system-x86 2>&1 | grep -E "newly installed|^E:"; apt-get clean
qemu-system-x86_64 --version | head -1; ls /dev/kvm 2>&1 | head -1
( time timeout 180 qemu-system-x86_64 -accel tcg -m 512 -display none -serial stdio -monitor none -cdrom /tmp/t.iso -boot d -no-reboot ) > /tmp/qemu.out 2>&1; echo "qemu rc=$?"
tr -d '\r' < /tmp/qemu.out | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | grep -a -E "GRAPHITE_ISO_SMOKE_OK|filesystem.squashfs|real" | head -5
cp /tmp/qemu.out /root/qemu.out
