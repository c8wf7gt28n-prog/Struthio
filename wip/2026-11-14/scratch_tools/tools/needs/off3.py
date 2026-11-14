import json, sys, re
d = json.load(open(sys.argv[1], encoding='utf-8'))
names = set(re.sub(r'^debs/', '', k).split('_')[0] for k in d['files'] if k.startswith('debs/'))
groups = {
 'base (INSTALL_DEBIAN.sh:46)': 'python3 python3-venv python3-pip libgl1 libegl1 libfontconfig1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 libxcb-xinerama0 poppler-utils',
 '--engineering (:47)': 'build-essential git nodejs iverilog clangd',
 '--math (:48)': 'libreoffice-calc libreoffice-writer default-jdk-headless',
 '--calc (:49)': 'libreoffice-calc',
 '--experiments (:50)': 'kicad',
 '--workers (:51)': 'bubblewrap dbus-user-session libpam-systemd',
 '--minimal-session (:52)': 'xserver-xorg xinit fluxbox x11-xserver-utils xauth dbus-x11 fonts-dejavu-core network-manager libgl1-mesa-dri',
 '--network-capture (:53)': 'wireshark-common',
 '--vulkan (:54)': 'libvulkan1 mesa-vulkan-drivers firmware-amd-graphics vulkan-tools libstdc++6 libgomp1 libssl3t64 zlib1g libzstd1 libgcc-s1 libc6',
 'other tools the code looks for': 'tesseract-ocr tcpdump ffmpeg ngspice yosys python3-tk openjdk-21-jre-headless',
}
for g, pk in groups.items():
    pk = pk.split()
    missing = [p for p in pk if p not in names]
    print(f"{g}: {len(pk)-len(missing)}/{len(pk)} in offline cache; missing: {missing}")
print(sorted(n for n in names if 'jdk' in n or 'jre' in n or 'java' in n or 'tesser' in n or 'writer' in n))
