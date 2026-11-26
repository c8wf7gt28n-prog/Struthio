## What the 1.0 System set adds

The System set grows for 1.0. It adds **136 Debian 13 amd64 packages (42.9 MB)** to the 396 the 0.8.x set already has.
Nothing is taken out: every 0.8.x file keeps its name and its checksum, so the `debs/` folder already on your USB stays
as it is and only gains files.

### Put it in place

1. Copy the 1.0 `debs/` files into `App/debs/`, beside the ones already there.
2. Use the 1.0 `App/OFFLINE_FILES.json` and `App/DEBIAN_USB.sha256`: they list the 0.8.x files and the new ones, and
   replace the earlier copies.
3. Check every file: `cd App && sha256sum --check --strict --quiet DEBIAN_USB.sha256`

### Install the packages

From the root console, in `App`:

```sh
bash INSTALL_GRAPHITE.sh --plan        # preview
bash INSTALL_GRAPHITE.sh --system      # install
```

It checks every file first, then gives apt only what this computer does not have yet: a package already installed at
the same or a newer version stays as it is. On the ThinkPad as 0.8.x left it, the preview should end with
`3 upgraded, 133 newly installed, 0 to remove`. apt uses only the files on the USB; nothing is downloaded.

Then **log out and log in again** before you start Graphite: your login session, the sound services and the system's
permission prompts start at login. After that, install Graphite from your ordinary account as before.

### What the new packages are for

- **USB drives** (see, open, eject safely): udisks2, eject.
- **The battery**: upower.
- **Sound** (volume, mute, output): pipewire, pipewire-pulse, wireplumber, and the sound card descriptions laptops need
  (alsa-ucm-conf, alsa-topology-conf).
- **Wi-Fi** (on, off, join): wpasupplicant and wireless-regdb. NetworkManager was already in the 0.8.x set.
- **Lock**: xsecurelock. Your password is checked by Debian's own login check; Graphite never sees it.
- **The system's permission prompts**: polkitd and lxpolkit.
- **Your login session**: libpam-systemd, so logind knows your session. Suspend, Lock, the permission prompts and sound
  rely on it.
- **Apps and windows**: xdg-utils (default programs), x11-utils (xprop and xdpyinfo, to read program windows).
- **Reading other programs**: at-spi2-core and python3-pyatspi (the desktop's accessibility), libreoffice-gtk3 (so
  LibreOffice shows its windows and dialogs to it), librsvg2-common (icons for GTK programs).
- **Kasandra's work in LibreOffice**: libreoffice-writer and python3-uno, at the same LibreOffice 25.2.3 as the 0.8.x
  set's Calc.
- The other packages are what these need.

### Good to know

- LibreOffice stays at the version the 0.8.x set installed (25.2.3, Debian's `deb13u9`), so the computer keeps one
  LibreOffice. Debian's security archive has newer LibreOffice fixes (`deb13u12`); this set does not carry them.
- If you have already updated LibreOffice from the network, the set cannot add Writer to it offline: the preview says
  so before anything changes. With the network, add them instead: `apt install libreoffice-writer libreoffice-gtk3 python3-uno`.
- Not tested. The set was resolved and checked in the build container only: every file against Debian's signed
  package lists, and apt's offline plan against stand-in copies of a ThinkPad as 0.8.x left it and of a Debian 13
  installed today. Nothing was installed anywhere, and nothing ran on your ThinkPad.
