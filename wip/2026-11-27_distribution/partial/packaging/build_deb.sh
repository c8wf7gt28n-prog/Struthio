#!/bin/bash
# Trial packaging of Graphite 1.0 as Debian packages (audit feasibility; nothing here is in the tree).
set -euo pipefail
W="$(cd "$(dirname "$0")" && pwd)"; SRC="$W/copy"; OUT="$W/debs"; ST="$W/stage"
rm -rf "$ST" "$OUT"; mkdir -p "$OUT"
VER=1.0-1
# ---------------- graphite (the program) ----------------
P="$ST/graphite"; mkdir -p "$P/DEBIAN" "$P/usr/lib/graphite" "$P/usr/bin" "$P/usr/share/applications" "$P/usr/share/doc/graphite" "$P/usr/share/icons/hicolor/256x256/apps"
# exactly the shipped payload: MANIFEST.json and every file it lists
python3 - "$SRC" "$P/usr/lib/graphite" <<'PY'
import json,shutil,sys,os
from pathlib import Path
src,dst=Path(sys.argv[1]),Path(sys.argv[2])
names=list(json.loads((src/'MANIFEST.json').read_text())['files'])+['MANIFEST.json']
for n in names:
    t=dst/n; t.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src/n,t)
print('payload files',len(names))
PY
cat > "$P/usr/bin/graphite" <<'SH'
#!/bin/sh
# Graphite: the Office window (what START_OFFICE.sh does), from the packaged program.
export ARC_LEDGER_EDITION=office ARC_LEDGER_OPEN="${ARC_LEDGER_OPEN:-office}"
export PYTHONPATH="/usr/lib/graphite${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m workbench.launch "$@"
SH
chmod 755 "$P/usr/bin/graphite"
cat > "$P/usr/share/applications/graphite.desktop" <<'D'
[Desktop Entry]
Type=Application
Name=Graphite
GenericName=Desktop workspace
Comment=The Graphite desktop and its assistant, Kasandra
Exec=graphite
Icon=graphite
Terminal=false
Categories=Office;Utility;
Keywords=desktop;workspace;assistant;
D
cp "$SRC/branding/graphite/graphite_icon_256.png" "$P/usr/share/icons/hicolor/256x256/apps/graphite.png"
cat > "$P/usr/share/doc/graphite/copyright" <<'C'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Graphite
Source: (the owner's repository)

Files: *
Copyright: 2026 the Graphite owner
License: GPL-2
 On Debian systems the full text of the GNU General Public License version 2
 is in /usr/share/common-licenses/GPL-2. See /usr/lib/graphite/RIGHTS.md and
 /usr/lib/graphite/THIRD_PARTY_NOTICES.md for the artwork that is kept back and
 the licences of the bundled fonts and runtimes.
C
printf 'graphite (%s) trixie; urgency=medium\n\n  * Trial package of Graphite 1.0 (audit).\n\n -- Graphite packaging trial <root@localhost>  Fri, 27 Nov 2026 12:00:00 +0000\n' "$VER" | gzip -9n > "$P/usr/share/doc/graphite/changelog.Debian.gz"
cat > "$P/DEBIAN/postinst" <<'S'
#!/bin/sh
set -e
if [ "$1" = configure ] && command -v py3compile >/dev/null 2>&1; then
    py3compile /usr/lib/graphite/workbench /usr/lib/graphite/sdk /usr/lib/graphite/pillkit >/dev/null 2>&1 || true
fi
exit 0
S
cat > "$P/DEBIAN/prerm" <<'S'
#!/bin/sh
set -e
find /usr/lib/graphite -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
exit 0
S
chmod 755 "$P/DEBIAN/postinst" "$P/DEBIAN/prerm"
find "$P/usr" -type d -exec chmod 755 {} +; find "$P/usr/lib/graphite" -type f ! -name '*.sh' -exec chmod 644 {} +; find "$P/usr/lib/graphite" -type f -name '*.sh' -exec chmod 755 {} +
SIZE=$(du -sk "$P/usr" | cut -f1)
cat > "$P/DEBIAN/control" <<C
Package: graphite
Version: $VER
Architecture: all
Maintainer: Graphite packaging trial <root@localhost>
Installed-Size: $SIZE
Section: x11
Priority: optional
Depends: python3 (>= 3.11), python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets, python3-pyside6.qtsvg, python3-pyside6.qtdbus, python3-pyside6.qtpdf, python3-pyside6.qtpdfwidgets, python3-cryptography (>= 41), python3-pypdf, poppler-utils, libgl1, libegl1, libxkbcommon-x11-0, libxcb-cursor0, fonts-dejavu-core, xdg-utils
Recommends: graphite-session, python3-pyside6.qtmultimedia, python3-pyside6.qtmultimediawidgets, libreoffice-calc, libreoffice-writer, libreoffice-gtk3, python3-uno, python3-docx, at-spi2-core, libvulkan1, mesa-vulkan-drivers, libgomp1
Suggests: python3-sympy, python3-z3, python3-pyside6.qtwebenginewidgets, wireshark-common, bubblewrap
Description: local-first desktop workspace with an assistant (Kasandra)
 Graphite is a desktop for one Debian computer: files, apps, the machine and
 settings in one window, with Kasandra, an assistant that works under the
 owner's grants. This is a trial package made during a packaging audit.
C
dpkg-deb --root-owner-group -Zxz --build "$P" "$OUT/graphite_${VER}_all.deb"
# ---------------- graphite-session (the login session) ----------------
S="$ST/graphite-session"; mkdir -p "$S/DEBIAN" "$S/usr/bin" "$S/usr/share/xsessions" "$S/usr/share/doc/graphite-session"
cat > "$S/usr/bin/graphite-session" <<'SH'
#!/bin/sh
# The Graphite session for a display manager or startx: the supervisor (LS_XSESSION.sh) of the packaged program.
exec /bin/bash /usr/lib/graphite/LS_XSESSION.sh "$@"
SH
chmod 755 "$S/usr/bin/graphite-session"
cat > "$S/usr/share/xsessions/graphite.desktop" <<'D'
[Desktop Entry]
Type=Application
Name=Graphite
Comment=Graphite is the whole desktop: log in to the Living Desktop
Exec=graphite-session
TryExec=graphite-session
DesktopNames=Graphite
D
cp "$P/usr/share/doc/graphite/copyright" "$S/usr/share/doc/graphite-session/copyright"
printf 'graphite (%s) trixie; urgency=medium\n\n  * Trial package of the Graphite session (audit).\n\n -- Graphite packaging trial <root@localhost>  Fri, 27 Nov 2026 12:00:00 +0000\n' "$VER" | gzip -9n > "$S/usr/share/doc/graphite-session/changelog.Debian.gz"
find "$S/usr" -type d -exec chmod 755 {} +
cat > "$S/DEBIAN/control" <<C
Package: graphite-session
Source: graphite
Version: $VER
Architecture: all
Maintainer: Graphite packaging trial <root@localhost>
Installed-Size: $(du -sk "$S/usr" | cut -f1)
Section: x11
Priority: optional
Depends: graphite (= $VER), xserver-xorg, xinit, fluxbox, x11-xserver-utils, xauth, dbus-user-session | dbus-x11, libpam-systemd, network-manager, wpasupplicant, wireless-regdb, libgl1-mesa-dri, udisks2, eject, upower, pipewire, pipewire-pulse, wireplumber, alsa-ucm-conf, alsa-topology-conf, xsecurelock, lxpolkit, polkitd, x11-utils, at-spi2-core, python3-pyatspi, librsvg2-common
Recommends: lightdm, lightdm-gtk-greeter, libreoffice-calc, libreoffice-writer, libreoffice-gtk3, python3-uno
Provides: x-session-manager
Description: Graphite as the login session
 The X session entry (shown by a display manager as "Graphite"), the session
 supervisor and the system services the Living Desktop uses: drives, sound,
 Wi-Fi, the battery, Lock and the system's permission prompts.
C
dpkg-deb --root-owner-group -Zxz --build "$S" "$OUT/graphite-session_${VER}_all.deb"
ls -l "$OUT"
