#!/bin/bash
echo "### (a) ldd of the bundled llama.cpp binaries on Debian 13.8 (no model loaded, nothing executed)"
mkdir -p /tmp/ll && cd /tmp/ll
for a in llama-b12359-bin-ubuntu-x64.tar.gz llama-b12359-bin-ubuntu-vulkan-x64.tar.gz; do
  rm -rf x && mkdir x && tar -xzf /usr/lib/graphite/runtimes/llama.cpp/b12359/$a -C x
  srv=$(find x -name llama-server -type f | head -1); d=$(dirname "$srv")
  echo "-- $a: $(find x -type f | wc -l) files, $(du -sm x | cut -f1) MB unpacked; server=$srv"
  ( cd "$d" && LD_LIBRARY_PATH=. ldd ./llama-server 2>&1 | grep -E "not found" | sort -u ; echo "   (missing libs listed above; none listed = all found)"; for so in ./*.so*; do LD_LIBRARY_PATH=. ldd "$so" 2>/dev/null | grep "not found"; done | sort -u | sed 's/^/   so: /' )
  strings -a "$srv" 2>/dev/null | grep -o -E "GLIBC_2\.[0-9]+" | sort -t. -k2 -n -u | tail -1
done
ldd --version | head -1
echo "### (b) the README's install line: INSTALL_DEBIAN.sh --minimal-session --vulkan package list against trixie main (simulation)"
PK="python3 python3-venv python3-pip libgl1 libegl1 libfontconfig1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 libxcb-xinerama0 poppler-utils xserver-xorg xinit fluxbox x11-xserver-utils xauth dbus-x11 fonts-dejavu-core network-manager libgl1-mesa-dri udisks2 upower pipewire pipewire-pulse wireplumber xsecurelock lxpolkit xdg-utils x11-utils at-spi2-core python3-pyatspi libpam-systemd wpasupplicant wireless-regdb eject librsvg2-common alsa-ucm-conf alsa-topology-conf"
VK="libvulkan1 mesa-vulkan-drivers firmware-amd-graphics vulkan-tools libstdc++6 libgomp1 libssl3t64 zlib1g libzstd1 libgcc-s1 libc6"
echo "-- without --vulkan:"; apt-get install -s --no-install-recommends $PK 2>&1 | grep -E "^E:|newly installed|Unable" | head -5
echo "-- with --vulkan (sources: main only, as debootstrap and a netinst without non-free-firmware give):"; apt-get install -s --no-install-recommends $PK $VK 2>&1 | grep -E "^E:|newly installed|Unable" | head -5
echo "-- sudo present in this minimal Debian? $(command -v sudo || echo no)"; echo "-- python3 in a minbase before installing graphite? (debootstrap minbase has none; this chroot has it only as graphite's dependency)"
echo "### (c) image tooling in Debian 13 (simulation: what apt would install)"
for set in "live-build" "debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools isolinux syslinux-common" "qemu-system-x86 qemu-utils ovmf" "lintian" "reprepro" "calamares calamares-settings-debian" "live-boot live-config linux-image-amd64"; do
  printf '%-95s ' "$set"; apt-get install --assume-no --no-install-recommends $set 2>&1 | grep -E "newly installed|Need to get|additional disk|^E:" | tr '\n' ' ' | sed -E 's/ and [0-9]+ not upgraded\.//'; echo
done
