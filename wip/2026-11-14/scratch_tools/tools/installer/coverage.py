"""Which apt package groups named in INSTALL_DEBIAN.sh are present in the offline deb cache; which requirement pins are in the wheel cache. Static."""
import json, re, sys
from pathlib import Path

T = Path(sys.argv[1]); R = Path(sys.argv[2])
off = json.loads((T / 'App/OFFLINE_FILES.json').read_text())['files']
debs = {k.split('/', 1)[1].split('_')[0] for k in off if k.startswith('debs/')}
wheels = {}
for k in off:
    if k.startswith('wheels/'):
        n, v = k.split('/', 1)[1].split('-')[:2]
        wheels[n.lower().replace('_', '-')] = v

groups = {
    'base (always, line 46)': 'python3 python3-venv python3-pip libgl1 libegl1 libfontconfig1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 libxcb-xinerama0 poppler-utils',
    '--engineering (47)': 'build-essential git nodejs iverilog clangd',
    '--math (48)': 'libreoffice-calc libreoffice-writer default-jdk-headless',
    '--calc (49)': 'libreoffice-calc',
    '--experiments (50)': 'kicad',
    '--workers (51)': 'bubblewrap dbus-user-session libpam-systemd',
    '--minimal-session (52)': 'xserver-xorg xinit fluxbox x11-xserver-utils xauth dbus-x11 fonts-dejavu-core network-manager libgl1-mesa-dri',
    '--network-capture (53)': 'wireshark-common',
    '--vulkan (54)': 'libvulkan1 mesa-vulkan-drivers firmware-amd-graphics vulkan-tools libstdc++6 libgomp1 libssl3t64 zlib1g libzstd1 libgcc-s1 libc6',
}
# confirm the literal lists against the script text so this table is not my transcription only
text = (R / 'INSTALL_DEBIAN.sh').read_text()
for label, pk in groups.items():
    names = pk.split()
    literal = all(re.search(r'(?<![\w.+-])' + re.escape(n) + r'(?![\w.+-])', text) for n in names)
    missing = [n for n in names if n not in debs]
    print(f"{label}: {len(names)} pkgs, all literal in script={literal}, missing from deb cache={missing or 'none'}")

print()
for req in sorted(R.glob('requirements-*.txt')):
    pins = [l.strip() for l in req.read_text().splitlines() if l.strip() and not l.startswith('#')]
    out = []
    for p in pins:
        m = re.match(r'([A-Za-z0-9_.-]+)\s*(==|>=)\s*([\w.]+)', p)
        n = m.group(1).lower().replace('_', '-')
        have = wheels.get(n)
        out.append(f"{p} -> cache {have or 'ABSENT'}")
    print(req.name, '|', '; '.join(out))
print('wheel cache:', wheels)

print()
qt_runtime = 'libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 libxcb-xinput0 libxcb-glx0 libxcb1 libx11-xcb1 libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0t64 libegl1 libgl1 libopengl0 libsm6 libice6 libxrender1 libxi6'.split()
print('commonly cited Qt6 xcb-platform system libraries -> in deb cache?')
for n in qt_runtime: print('   ', n, 'yes' if n in debs else 'NO')
for n in ('sudo', 'wpasupplicant', 'iwd', 'lightdm', 'gdm3', 'sddm', 'xdm', 'nodm', 'slim', 'linux-image-amd64', 'initramfs-tools', 'firmware-realtek', 'firmware-atheros', 'firmware-iwlwifi', 'firmware-misc-nonfree', 'firmware-mediatek', 'firmware-linux-free', 'systemd-sysv', 'libpam-systemd', 'systemd-timesyncd', 'libnss-systemd', 'xserver-xorg-legacy', 'libasound2t64', 'libpulse0', 'libxcomposite1', 'libxdamage1', 'libxtst6', 'libnss3', 'pciutils', 'console-setup', 'kbd'):
    print('   extra check', n, 'yes' if n in debs else 'NO')
