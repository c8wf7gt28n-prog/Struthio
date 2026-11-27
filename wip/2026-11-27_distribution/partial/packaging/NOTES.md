# Packaging, install and image: audit notes (key: packaging)

Audited 27 November 2026 on the tree at commit 9a83331 (branch claude/epic-galileo-c7k11y). Read only on the repository.
Everything that ran, ran on a throwaway copy or inside a Debian 13.8 chroot under this folder; both are deleted.
Evidence files kept beside this note: `build_deb.sh` (the trial packaging), `deb_info.txt`, `deb_contents.txt`,
`lintian_graphite.txt`, `lintian_session.txt`, `apt_sim.txt`, `apt_install_graphite.log`, `debootstrap.log`,
`t1.out` … `t9.out`, `venv_test_*.out`, `versions.txt`, `tools.txt`, `evidence/` (the scripts run in the chroot and the
unittest outputs), `debs/` (the small session .deb, the folder repository's Packages, Release, InRelease).

## 1. Verdict

Graphite today is an application that the owner installs on his own ThinkPad from a hand-assembled kit. It is not yet
software a stranger can install, and it is not a distribution: there is no package, no graphical login, no install
medium, no signature, and the offline kit cannot be rebuilt by anyone outside this build container.

The good news, found by trying: the distance is engineering, not research. In this container I built a `.deb` of the
whole 1.0 payload, checked it with Debian 13's own lintian, installed it with `apt` inside a real Debian 13.8 chroot
with every dependency resolved from deb.debian.org, and Graphite started there on **Debian's own** Python 3.13.5 and
PySide6 6.8.2.1 (no venv, no wheels): `graphite --version`, the doctor, the offscreen start (`ARC1_LAUNCH_OK qt`),
payload VERIFIED from a root-owned `/usr/lib/graphite`, nothing written into the program folder, and eight test modules
gave exactly the results the pinned-wheel venv gives. A signed folder repository (the USB stick layout) was accepted by
apt 3.0, and a hybrid BIOS/UEFI ISO was assembled and booted to GRUB in QEMU without KVM.

The single biggest gap: **there is no real package and no graphical way in**. Power on gives a text login, and the
program lives in `~/Applications` with a 645 MB private copy of Qt per release.

## 2. What exists today (read)

- `INSTALL_LS.py` (365 lines): verifies ZIP parts against `RELEASE_PARTS.json`, restores into a NEW folder
  (`--target`, refuses an existing one, line 148), then runs `INSTALL_DEBIAN.sh --quick` (line 329). Offline mode needs
  `OFFLINE_FILES.json` + `debs/` + `wheels/` (lines 191-216). Refuses root (line 316) except `--system-only`.
- `INSTALL_DEBIAN.sh`: builds an apt list by option and runs `sudo apt-get update` / `sudo apt-get install` (lines
  63-64), then `INSTALL_LEDGER.sh`.
- `INSTALL_LEDGER.sh`: `python3 -m venv .venv` inside the program folder (line 37), `pip install -r requirements-qt.txt`
  (PySide6==6.8.3, cryptography==50.0.2, pypdf==7.0.0) from PyPI or `--no-index --find-links` (lines 44-46), then import
  and payload checks.
- `PREPARE_DEBIAN.sh` (root console): checks `DEBIAN_USB.sha256`, gives apt only the debs that move the system forward,
  empty sources (no network). Debian 13 amd64 only (lines 9-11).
- `wip/build_tools/kit_1.0/INSTALL_GRAPHITE.sh`: the kit's two phases (`--system` as root, then the user phase:
  `--offline --system-ready --minimal-session --vulkan --calc` into `$HOME/Applications/Graphite-0.2a13`, a placeholder
  that `wip/build_tools/cut_1.0.sh` rewrites with sed).
- `START_MINIMAL_DEBIAN.sh` (text login: `startx LS_XSESSION.sh --`) and `LS_XSESSION.sh` (the supervisor: D-Bus
  session, Fluxbox, lxpolkit, Graphite restarted with back-off, `last-session.json`).
- `tools/package_graphite.py` (seed + MANIFEST.json + full ZIP), `tools/package_release_parts.py` (15 MB volumes).
- The kit: 532 debs (348 MB) + 8 wheels (262 MB: PySide6 Addons alone 160 MB). The 1.0 kit **carries only the 136 new
  debs**; the other 396 and the wheels are "already on your USB" from 0.8.x. `SYSTEM_SET_1.0.json` records the 136.
- No `.desktop` file, no `/usr/share/xsessions` entry, no systemd unit, no `debian/` directory anywhere in the tree
  (`git ls-files` shows only `LS_XSESSION.sh` for the pattern desktop|xsession|lightdm|systemd|service|debian|autostart).
- No word about uninstalling in README.md, GETTING_STARTED.md or docs/ (grep "uninstall": nothing).

## 3. Feasibility, by trying (what I ran and what it printed)

Host: Ubuntu 24.04, root, 4 cores, no `/dev/kvm`, no docker daemon. Present: `dpkg-deb`, `dpkg-scanpackages`, `gpg`,
`unshare`, `chroot`, `mount`, `ar`, `xz`, loop devices (`/dev/loop-control`, `losetup -f` → `/dev/loop0`). Absent:
lintian, debootstrap, mmdebstrap, fakeroot, xorriso, mksquashfs, live-build, qemu, apt-ftparchive, reprepro.
Nothing was installed on the host; missing tools were fetched from deb.debian.org and run from this folder or inside
the chroot.

| Question | Result |
|---|---|
| Is dpkg-deb here? can a .deb be built? | Yes. `build_deb.sh` built `graphite_1.0-1_all.deb` (139,922,800 bytes, the 1,560 payload files under `/usr/lib/graphite`, Installed-Size 172,088 kB) and `graphite-session_1.0-1_all.deb` (1,988 bytes) in 33 s with `dpkg-deb --root-owner-group -Zxz --build`. |
| lintian? | Not on the host. Installed inside the chroot (`apt-get install lintian`: 208 packages, 207 MB), version 2.122.0+deb13u1. graphite: 3 E (all three are my placeholder maintainer address), 15 W, 245 I, 11 s. session: the same 3 E, 2 W, 3 I. The real warnings are listed in section 6. |
| debootstrap available or installable? | Not installed. Downloaded `debootstrap_1.0.141_all.deb` and `debian-archive-keyring_2025.1_all.deb` (sha256 checked against trixie's Packages index), unpacked them here, ran with `DEBOOTSTRAP_DIR`. |
| Does a Debian 13 chroot work here? | Yes. `debootstrap --variant=minbase trixie` finished in 56 s, 220 MB, `Valid Release signature (key id 41587F7D…)`, `/etc/debian_version` 13.8. Entered with `unshare --mount --pid --fork` + proc, `/dev` rbind, tmpfs `/run` and `/tmp`: all allowed. |
| Does apt resolve the .deb's Depends from deb.debian.org? | Yes (https through the proxy, `Acquire::https::CaInfo` set to the proxy bundle). Simulations: graphite alone `181 newly installed, 118 MB to get, 661 MB disk`; graphite + graphite-session without Recommends `416 newly installed, 210 MB, 1001 MB`; with Recommends (LightDM, LibreOffice) `863 newly installed, 527 MB, 2102 MB`. |
| Real install? | `apt-get install -y /debs/graphite_1.0-1_all.deb`: rc 0 in 57 s, `Status: install ok installed`. Python 3.13.5, `PySide6 6.8.2.1 Qt 6.8.2 cryptography 43.0.0 pypdf 5.4.0`. graphite-session was simulated only (its 235 further packages did not fit the disk rule). |
| Does Graphite run from the package? | As an ordinary user `tester`: `graphite --version` → `Graphite 1.0` (from `/` and from `~`); `QT_QPA_PLATFORM=offscreen graphite --check` → `ARC1_LAUNCH_OK qt` (3.4 s); `verify(/usr/lib/graphite)` → `payload VERIFIED 1559 []`, seed `VERIFIED_SOURCE_BINDINGS` (after postinst's py3compile); `find /usr/lib/graphite -newer marker` → nothing; the workspace appeared in `~tester/Concern/Office`, the profile in `~tester/.config/arc1-workbench`. `LEDGER.sh doctor --qt-check` → `Disposable Qt check: PASSED`, but the doctor ends `NEEDS_ATTENTION` (rc 2): `PySide6: DIFFERENT_VERSION (expected 6.8.3)`, `cryptography: DIFFERENT_VERSION (expected 50.0.2)`. |
| Tests on Debian's stack | test_install_media (17), test_startup_scripts, test_launcher (17), test_viewer_kinds, test_documents, test_deployment: OK. test_session_start: 2 failures of 28; test_graphite: 1 failure + 1 error of 29. The same four fail identically under the pinned venv (PySide6 6.8.3) on the same tree, so they are not caused by Debian's versions (they are for the tests auditor). First run failed more: `ModuleNotFoundError: No module named 'PySide6.QtTest'` until `python3-pyside6.qttest` was installed (finding 9). |
| The session supervisor from the package | `LS_XSESSION.sh` run from `/usr/lib/graphite` with a stand-in fluxbox, offscreen: `session.log` → `Graphite started (process 26)`; TERM to the supervisor → `last-session.json` `{"status":143,…,"restarts":0}`. Left running afterwards: `/usr/bin/python3 -m workbench.host_service --root /home/tester/Concern/Office` (finding 17). |
| The bundled model runtime on Debian 13 | Both llama.cpp b12359 archives unpack (57 MB, 96 MB); `ldd llama-server` and every `.so`: nothing missing on 13.8 once libgomp1, libssl3t64, zlib1g, libzstd1, libstdc++6 (and libvulkan1 for the Vulkan build) are there; highest glibc symbol 2.34 (Debian 13 has 2.41). Nothing was executed, no model loaded. |
| A signed apt repository in a folder | `dpkg-scanpackages` + `apt-ftparchive release`. Unsigned: `E: The repository 'file:/debs ./ Release' is not signed.` Signed with a throwaway ed25519 key (`gpg --clearsign` → InRelease, key in `/usr/share/keyrings`, `signed-by=`): `apt-get update` with only that source succeeds, `apt-cache policy` shows both packages from `file:/debs`, `apt-get install -s graphite-session` plans the install by name. (gpg on the host could not start its agent because this folder's path is too long for a socket; done inside the chroot.) |
| Remove | `apt-get remove -y graphite`: `/usr/lib/graphite` gone (0 files), `~tester/Concern/Office`, `~/.config/arc1-workbench`, `~/.local/state/ledger-slate` untouched. |
| squashfs / xorriso / GRUB | Installed in the chroot (18 packages): `mksquashfs` (xz) OK; `grub-mkrescue` rc 0 → a 33.6 MB ISO with two El Torito images (BIOS and UEFI). |
| QEMU without KVM | `qemu-system-x86` 10.0.13 installed in the chroot (32 packages, 138 MB). `qemu-system-x86_64 -accel tcg -display none -serial stdio -cdrom t.iso` printed `GRAPHITE_ISO_SMOKE_OK` and listed `filesystem.squashfs` from GRUB; rc 0 in 1.45 s. |
| live-build | Installable (6 packages, 6 MB; simulated). Not run: a real live image (kernel 117 MB download, a 2 GB root, the squashfs, the ISO) needs 4 to 6 GB of scratch; the disk rule left 1.2 GB. Calamares is in Debian 13 (3.3.14; 148 packages, 227 MB). |
| Not possible here | A real X server, a display manager's greeter, a boot to the desktop, suspend, Wi-Fi, firmware, the ThinkPad. A VM boot of a full image to the Graphite window is possible in principle under TCG (slow: minutes) given the disk. |

Disk: 76.9 % before, peak 78.6 %, 75.8 % after cleaning.

## 4. What Debian 13 really has (trixie 13.8, index of 21 November 2026)

| Graphite pins (wheels) | Debian 13 | Note |
|---|---|---|
| PySide6 6.8.3 | `python3-pyside6.*` 6.8.2.1-4, **one package per Qt module** (qtcore, qtgui, qtwidgets, qtsvg, qtdbus, qttest, qtpdf, qtpdfwidgets, qtmultimedia, qtmultimediawidgets, qtwebenginecore, qtwebenginewidgets …), tied to Qt 6.8.2 (`qt6-base-private-abi (= 6.8.2)`) | ran Graphite; no `python3-pyside6` umbrella to depend on |
| cryptography 50.0.2 | python3-cryptography 43.0.0-3+deb13u1 | test_deployment OK |
| pypdf 7.0.0 | python3-pypdf 5.4.0-1 | test_documents OK |
| python-docx 1.2.0 | python3-docx 1.1.2 | not tried |
| sympy 1.14.0, z3 4.15.4 | python3-sympy 1.13.3, python3-z3 4.13.3 | not tried |
| wasmtime 50.0.1 | absent | stays a wheel, or the experiment room is optional |
| llama.cpp | absent | the bundled archives stay |
| Python | 3.13.5 | within 3.11 to 3.13 |
| LibreOffice | 4:25.2.3-2+deb13u9 in main, deb13u12 in security | the kit pins u9 |
| firmware-amd-graphics | not in `main` (non-free-firmware) | finding 7 |
| lightdm 1.32.0, lightdm-gtk-greeter 2.0.9, greetd 0.10.3, sddm, nodm 0.13, xdm | present | |
| lintian 2.122.0, debootstrap 1.0.141, live-build 1:20250505, xorriso 1.5.6, squashfs-tools 4.6.1, qemu-system-x86 10.0.13, reprepro, calamares 3.3.14, dh-python | present | |
| fonts-inter 4.1, fonts-opendyslexic | present | the tree bundles its own copies (lintian: duplicate-font-file) |

## 5. The design: "installs like real Debian software"

### 5.1 Packages (one source package `graphite`, `debian/` in the tree)

| Package | Arch | Holds | Depends (checked against trixie) |
|---|---|---|---|
| `graphite` | all | the program under `/usr/lib/graphite` (one root, so MANIFEST.json still verifies), `/usr/bin/graphite` (what START_OFFICE.sh does), `/usr/bin/graphite-doctor` (LEDGER.sh), `/usr/share/applications/graphite.desktop`, the icon, `/usr/share/doc/graphite/copyright` | python3 (>= 3.11), python3-pyside6.qtcore, .qtgui, .qtwidgets, .qtsvg, .qtdbus, **.qttest**, .qtpdf, .qtpdfwidgets, python3-cryptography (>= 41), python3-pypdf, poppler-utils, **procps**, libgl1, libegl1, libxkbcommon-x11-0, libxcb-cursor0, fonts-dejavu-core, xdg-utils. Recommends: graphite-session, graphite-llama-runtime, python3-pyside6.qtmultimedia, .qtmultimediawidgets, libreoffice-calc, libreoffice-writer, libreoffice-gtk3, python3-uno, python3-docx, at-spi2-core. Suggests: python3-sympy, python3-z3, python3-pyside6.qtwebenginewidgets, wireshark-common, bubblewrap |
| `graphite-session` | all | `/usr/share/xsessions/graphite.desktop` (`Exec=graphite-session`, `DesktopNames=Graphite`), `/usr/bin/graphite-session` (LS_XSESSION.sh), `/usr/bin/graphite-startx` (START_MINIMAL_DEBIAN.sh, for the text console), the systemd user unit of 5.4 | graphite (= version), xserver-xorg, xinit, fluxbox, x11-xserver-utils, xauth, dbus-user-session, libpam-systemd, network-manager, wpasupplicant, wireless-regdb, libgl1-mesa-dri, udisks2, eject, upower, pipewire, pipewire-pulse, wireplumber, alsa-ucm-conf, alsa-topology-conf, xsecurelock, lxpolkit, polkitd, x11-utils, at-spi2-core, python3-pyatspi, librsvg2-common, xdg-user-dirs, xterm (the failsafe). This is `SYSTEM_SET_1.0.json`'s `asked_for` plus the 0.8.x `--minimal-session` list of INSTALL_DEBIAN.sh:52-54. |
| `graphite-llama-runtime` | amd64 | `runtimes/llama.cpp/b12359` (57 MB) | libgomp1, libssl3t64, libstdc++6, zlib1g, libzstd1, libvulkan1; Recommends mesa-vulkan-drivers. Section non-free or contrib-like in the own archive is not needed (MIT); it is prebuilt upstream binaries, so it can never go into Debian main as is. |
| `graphite-desktop` | all | nothing but dependencies and `/usr/share/lightdm/lightdm.conf.d/50-graphite.conf` (`user-session=graphite`), the greeter's background | graphite, graphite-session, lightdm, lightdm-gtk-greeter; Recommends: firefox-esr, libreoffice-calc, libreoffice-writer, libreoffice-gtk3, python3-uno, fonts-liberation, fonts-crosextra-carlito, fonts-crosextra-caladea, fonts-noto-core, fonts-noto-color-emoji, hunspell-en-us, cups, system-config-printer, bluez, libspa-0.2-bluetooth, rtkit, gvfs, ntfs-3g, exfatprogs, dosfstools, unzip, zip, 7zip, firmware-linux-free, firmware-amd-graphics, firmware-iwlwifi, firmware-realtek, firmware-misc-nonfree, amd64-microcode, intel-microcode |
| `graphite-archive-keyring` | all | `/usr/share/keyrings/graphite-archive-keyring.gpg`, `/etc/apt/sources.list.d/graphite.sources` (deb822, `Signed-By`) | |

Sizes measured: graphite alone pulls 181 packages / 661 MB on a bare system; graphite + session 416 / 1.0 GB; the whole
desktop with LightDM and LibreOffice 863 / 2.1 GB. Compare today: each `~/Applications/Graphite-x.y` is 170 MB of
program plus a venv whose PySide6 alone is 645 MB.

Build: `debhelper-compat (= 13)`, `dh $@ --with python3` with `dh_python3 /usr/lib/graphite` for byte-compiling
(my trial postinst called `py3compile` by hand; payload still VERIFIED afterwards because `verify` only checks listed
files). `debian/rules` must rebuild the seed and MANIFEST.json after any Debian patch
(`tools/package_graphite.py --manifest-only`, `tools/record_registry.py`), because the install scripts are seed inputs
(`workbench/stacy_foundation.py:60-61`): Build-Depends on the python3-pyside6 modules. `debian/tests/control`
(autopkgtest) runs `tools/run_tiers.py 0` against the installed tree: proven workable here.

postinst/prerm: byte-compile on configure; remove `__pycache__` on remove (verified: nothing left). No maintainer
script touches a home folder. `graphite-desktop.postinst` may ask one debconf question (log in automatically as the
first user? default no) and writes `/etc/lightdm/lightdm.conf.d/60-graphite-autologin.conf`; purge removes it.

### 5.2 The graphical way in

Recommended: **LightDM with lightdm-gtk-greeter** (small, in Debian 13, GTK 3 which the set already carries for lxpolkit
and LibreOffice, logind-aware so the session is "active" for polkit, udisks2 and NetworkManager, autologin is one
line). It runs the session through `/etc/X11/Xsession`, so `Xsession.d` runs: the user bus, `xdg-user-dirs-update`,
the D-Bus activation environment. `LS_XSESSION.sh` already works as a session client there: it needs `DISPLAY` (set)
and skips `dbus-run-session` when `DBUS_SESSION_BUS_ADDRESS` is set (it is, with dbus-user-session).
The greeter is themed to Day (background, Inter); later a Graphite greeter (LightDM has a greeter API; greetd is the
alternative if a Qt greeter is wanted).

Kept for the owner, who is at home in DOS: the text-console way as an option, like typing `win`: `graphite-startx` on
tty1, and optionally autologin on tty1 (`/etc/systemd/system/getty@tty1.service.d/autologin.conf`) with
`/etc/profile.d/graphite-startx.sh` that starts it only when the user has `~/.config/graphite/start-at-login`.

Needed in the tree for the display-manager way:
- the leave group's words by how the session was started (`workbench/session_power.py:196-202`): under a display
  manager "Return to Debian" is "Log out" (it ends at the greeter), and the text of
  `workbench/system_settings_qt.py:279` ("START_MINIMAL_DEBIAN.sh in Graphite's folder starts this session again")
  is wrong;
- the supervisor's give-up message (`LS_XSESSION.sh:189`) goes to stderr, which a display manager hides: show it (a
  small window with Try again, Open a terminal, Log out), and write it for the next start to show;
- a failsafe: `xterm` in Depends and a "Graphite (safe start)" session entry.

### 5.3 Where files go, and what must change in the tree

Works unchanged (verified): a root-owned read-only `/usr/lib/graphite`, system python without `.venv`
(`START_OFFICE.sh` falls back to `python3`), any working directory with `PYTHONPATH`, the model runtime extracted to
`~/.config/arc1-workbench/runtimes/<build>` (`workbench/brain_runtime.py:74,87`), the workspace in `~/Concern/Office`.

Must change:
1. `workbench/doctor.py:61` and `workbench/hatch_readiness.py:99`: exact pins (`'6.8.3'`, `'50.0.2'`,
   `qVersion()=='6.8.3'`) → tested ranges (PySide6 6.8.2 to 6.8.x, cryptography >= 43, pypdf >= 5.4).
2. `workbench/launch.py:20`: `INSTALL = APP.parent / 'install.json'` becomes `/usr/lib/install.json`; and the error
   log's second place (`LS_XSESSION.sh:44`, `launch.py` `error_log_candidates`) becomes `/usr/lib/launch-error.log`.
   Use `/etc/graphite/install.json` and only the XDG state folder.
3. Words that name the scripts: `workbench/launch.py:53` ("Run bash INSTALL_LEDGER.sh --quick to repair the Qt
   runtime"), `START_MINIMAL_DEBIAN.sh:19,21` ("Run INSTALL_DEBIAN.sh --minimal-session --quick"),
   `LS_XSESSION.sh:189`, `workbench/system_settings_qt.py:279`. A packaged install says `apt install --reinstall
   graphite` / `apt install graphite-session`.
4. The in-app signed updater (`workbench/release_updates.py`, Arrange ▸ Exchange & deployment) must say "updates come
   from the system's packages" when the program is owned by dpkg.
5. `workbench/release_integrity.py:26-45` checks one root against one manifest and calls any symlink "linked path":
   a split (runtime in its own package) needs the manifest to know optional groups, or the runtime stays in one tree
   provided by two packages into the same root (that works: dpkg only cares about file ownership).
6. `tests_integrated/` (3 MB), `build/` evidence (19 MB), `.gitignore`, `tools/` are in the payload; move the tests to
   autopkgtest and drop `.gitignore`; `arc1` is not executable (lintian).
7. `requirements-*.txt` stay for the tarball route; add a `debian/control` kept in step, and one CI job that runs the
   tiers in a trixie chroot on Debian's versions.

### 5.4 systemd user units

- `graphite-host.service` (user): `ExecStart=/usr/bin/python3 -m workbench.host_service --root %h/Concern/Office`,
  `PartOf=graphical-session.target`, so the coordinator stops at logout and is restarted by an upgrade
  (`deb-systemd-helper --user`), instead of being spawned detached by `workbench/host_client.py:135` and surviving the
  session (observed).
- PipeWire, WirePlumber, the user bus: Debian's own user units, enabled by the packages; nothing to add.
- The session itself stays a display-manager session (not a systemd unit); `graphical-session.target` is started by the
  supervisor so user units bound to it work.

### 5.5 The apt repository on the USB stick

```
GRAPHITE/                               (ext4 or exFAT: apt only reads)
  dists/graphite/InRelease              signed with the Graphite archive key
  dists/graphite/main/binary-amd64/Packages.xz        graphite, graphite-session, graphite-desktop, graphite-llama-runtime, keyring
  dists/graphite/debian/binary-amd64/Packages.xz      the mirrored closure from Debian 13.x (about 860 debs, 530 MB with the desktop)
  pool/main/g/graphite/*.deb
  pool/debian/…/*.deb                   Debian's own files, byte for byte (their sha256 in Packages)
  graphite-archive-keyring.gpg
  install.sh                            as root: copy the key, write /etc/apt/sources.list.d/graphite-usb.sources
                                        (Types: deb / URIs: file:/media/… / Suites: graphite / Components: main debian /
                                        Signed-By: …), apt-get update, apt-get install graphite-desktop
```

Made with `reprepro` (or `apt-ftparchive`), the closure collected with `apt-get install --download-only
graphite-desktop` in a clean trixie chroot: the chroot and apt resolution were proven here. This replaces
`OFFLINE_FILES.json`, `DEBIAN_USB.sha256`, `SYSTEM_SET_1.0.json` and PREPARE_DEBIAN.sh's version arithmetic: apt does
it. With the network, the same computer also sees deb.debian.org and takes the newer file. The stick's snapshot is
rebuilt at every Debian point release (13.9 …) by one script.

### 5.6 Upgrade from the `~/Applications` install, and uninstall

- The workspace, the profile and the state are already outside the program (`~/Concern`, `~/.config/arc1-workbench`,
  `~/.local/state/ledger-slate`): the packaged Graphite opens the same workspace as it is. Nothing to migrate.
- On its first packaged start Graphite lists `~/Applications/Graphite-*` and offers to remove them (each about 0.8 GB
  with its venv), and old `runtimes/<build>` folders in the profile (about 150 MB a build).
- A later upgrade is `apt upgrade` (the repository offers 1.0-2 over 1.0-1); the supervisor restarts the window.
- Uninstall: `apt remove graphite graphite-session graphite-desktop` leaves every home untouched (verified); a page in
  the guide says what the user may delete by hand. Today there is no uninstall path or page at all.

### 5.7 The image

`live-build` (trixie, areas `main non-free-firmware`), package list `graphite-desktop`, the folder repository in
`config/packages.chroot`, LightDM autologin for the live user, Calamares (`calamares-settings-debian`) as "Install
Graphite" from the live session, GRUB for BIOS and UEFI; firmware and microcode on the image. The owner's "DOS way":
a boot entry "Graphite (text console)". Feasible in a container like this one with 6 GB of scratch; boot smoke in QEMU
(TCG) works here.

## 6. lintian on the trial package (the real ones)

- W `package-contains-vcs-control-file` `usr/lib/graphite/.gitignore`
- W `script-not-executable` `usr/lib/graphite/arc1`
- W `duplicate-font-file` × 6 (Inter × 4 → fonts-inter, OpenDyslexic × 2 → fonts-opendyslexic);
  W `opentype-font-prohibits-installable-embedding` × 2 (OpenDyslexic)
- W `jar-not-in-usr-share`, W `classpath-contains-relative-path` (`runtimes/office-uno/libreoffice-25.2.0.jar`)
- W `no-manual-page` (graphite, graphite-session)
- I `package-contains-documentation-outside-usr-share-doc` × 220, `font-outside-font-dir` × 9, `extra-license-file` × 7
- lintian does not look inside `runtimes/llama.cpp/b12359/*.tar.gz`: prebuilt upstream binaries, fine for an own
  archive, never for Debian main.

## 7. The faults a stranger would hit today, in the order they would meet them

1. **Nothing to download.** No public release exists (docs/MINIMAL_DEBIAN_INSTALL_01.md: "A public Graphite release has
   not been published yet"). The 1.0 kit is ZIPs under 15 MB to be put in place by hand in five steps.
2. **The offline kit is incomplete without the owner's stick.** `OFFLINE_FILES.json` lists 540 files; the 1.0 kit carries
   136 debs; the other 396 debs and all 8 wheels exist only in the owner's Graphite_Transfer folder. PREPARE_DEBIAN.sh
   stops: "The USB dependency files did not match."
3. **They must install Debian 13 themselves first**, text installer, and mount the stick by hand at the root console
   (`lsblk -f`, `mount`).
4. **The online way needs sudo.** A Debian installed with a root password has no sudo. Ran it: `INSTALL_DEBIAN.sh: line
   63: sudo: command not found`, rc 127, as the ordinary user **and as root** (the script calls sudo even when it is
   root, and INSTALL_LEDGER.sh refuses root). INSTALL_LS.py then says only "Dependency installation returned status 127".
5. **The README's own command fails without non-free-firmware.** `--vulkan` adds `firmware-amd-graphics`
   (INSTALL_DEBIAN.sh:57); with `main` only (a VM, an Intel machine, a netinst that needed no firmware): `E: Package
   'firmware-amd-graphics' has no installation candidate` and the whole apt step fails. It is also the wrong firmware
   for any machine that is not an AMD one.
6. **A failed first try blocks the second.** The target folder now exists: "Choose a new installation folder".
7. **pip from PyPI**: 256 MB of wheels by version, without hashes (INSTALL_LEDGER.sh:46), over a second network source.
8. **No "log out and in" on the online way.** PREPARE_DEBIAN.sh says it (line 87); INSTALL_LS.py ends with "Start with:
   bash …/START_MINIMAL_DEBIAN.sh" (line 358) right after installing libpam-systemd, PipeWire and polkit.
9. **Every start is a typed command at a text login**: `bash "$HOME/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh"`.
10. **Wi-Fi the installer set up is not Graphite's.** A netinst writes the interface into `/etc/network/interfaces`;
    NetworkManager then leaves it unmanaged, so the Machine's Wi-Fi shows a device it cannot control (real hardware
    needed to confirm).
11. **Their hardware is not the ThinkPad.** Only `firmware-amd-graphics` is in the set: no Intel or Realtek Wi-Fi
    firmware, no microcode. The docs speak of "the ThinkPad" throughout; INSTALL_GRAPHITE.sh fixes `--vulkan --calc`.
12. **Debian moves.** The set is pinned to one day's versions; the documented case is LibreOffice (u9 in the kit, u12 in
    security: "the offline set cannot add Writer"). Any later point release can do the same to another package.
13. **Nothing checks who made it.** The debs are checked against a sha256 list that sits beside them, unsigned; the ZIP
    parts likewise unless the user has a checksum from elsewhere.
14. **amd64 only, Debian 13 only** (PREPARE_DEBIAN.sh:11; the online script would try on Ubuntu and fail on names such
    as libssl3t64).
15. **A new 0.8 GB folder per release, no clean-up, no uninstall.**
16. **Old names everywhere**: INSTALL_LS.py, LEDGER.sh, `~/.config/arc1-workbench`, `~/.local/state/ledger-slate`,
    "Use INSTALL_LEDGER.sh on a non-Debian system"; docs/MINIMAL_DEBIAN_INSTALL_01.md still installs "Graphite_0.1"
    and says "about 77 MB" (the parts are about 140 MB now).

Not a fault: `~/Concern` is not an assumption about the owner. On a new account the Office workspace is created at
`~/Concern/Office` at the first start (seen in the chroot). The name is unusual for a newcomer, nothing more.

## 8. Findings, ranked (the structured result carries the short form)

Blockers
1. No Debian package: program in `~/Applications`, private venv from PyPI wheels, no dpkg ownership, upgrade or removal.
2. No graphical way in: text login and a typed command at every boot; no xsessions entry, no display manager.
3. The release cannot be rebuilt or completed by anyone else: kit depends on the owner's 0.8.x stick; cut scripts under
   `wip/` with this container's paths.
4. No install medium (ISO) and no signed repository: nothing a stranger can boot or `apt install`.

Major
5. Unsigned media (apt 3.0 refuses an unsigned repository; today's kit has no publisher signature).
6. Online installer needs sudo (fails as user and as root without it).
7. README's command fails without non-free-firmware (`firmware-amd-graphics`).
8. Doctor and readiness demand the exact wheel versions: NEEDS_ATTENTION on Debian's own packages.
9. Depends that only trying finds: `python3-pyside6.qttest` (Kas's hand: `workbench/desk_scene.py:379`), `procps`
   (`workbench/operation_stop.py:87,149`), the llama runtime's libraries.
10. Under a display manager the session's words and its failure message are wrong or invisible.
11. The offline System set is one day's snapshot; it breaks at point releases.
12. The System set is the ThinkPad's minimum, not a desktop for a Windows user (no browser, printing, Bluetooth, Office
    fonts, codecs, spelling, archive tools, xdg-user-dirs, other firmware).
13. NetworkManager and the installer's `/etc/network/interfaces` (real hardware).
14. Program-relative paths and the in-app updater assume a writable program folder the user owns.
15. Seed and manifest binding: a distributor's patch makes "seed/source binding is not current" unless the package build
    rebuilds them.
16. No relogin note on the online path; first session may start without logind's session (real hardware).
17. The coordinator (`workbench.host_service`) outlives the session; not a user unit; an upgrade leaves old code running.
18. Rights: `games/struthio` has no licence assigned and the artwork is "copy unchanged with Graphite only"; a mirror or
    a derivative cannot ship the package as it is.

Minor
19. Each release folder costs 0.8 GB and is never cleaned; old model runtime caches stay.
20. pip without hashes on the online path.
21. lintian's list (section 6), tests and build evidence in the runtime payload.
22. Docs drift and old names (Graphite_0.1, 0.2a13 placeholder, 77 MB, INSTALL_LS.py, ledger-slate).
23. amd64 only; the model runtime refuses other architectures.
24. `/usr/lib/install.json` would be read as install info in a packaged layout (PATH additions).

## 9. What can only be confirmed on real hardware (or a VM with a screen)

LightDM greeting and starting the Graphite session; autologin; rootless Xorg through logind after a fresh install;
Lock, Suspend and the permission prompts in a display-manager session; PipeWire with the user bus; NetworkManager
against an installer-written interfaces file; firmware for Wi-Fi and graphics; the live ISO's boot to the desktop and
Calamares' install; the Vulkan runtime on the Radeon.

## 10. Suggested order of work

1. `debian/` in the tree + `tools/build_deb.sh` (start from `build_deb.sh` here); fix the pins, the paths, the words
   (5.3). CI: build in a trixie chroot, lintian, install, tiers on Debian's versions. (M)
2. `graphite-session` with the xsessions entry, LightDM configuration, the leave words, the visible failure (5.2). (M)
3. The signed repository on a stick + `install.sh`; retire the kit scripts (5.5). (M)
4. `graphite-desktop` and its Recommends (the Windows user's everyday). (S)
5. The live ISO with Calamares, boot-smoked in QEMU, then walked on the ThinkPad. (L)
