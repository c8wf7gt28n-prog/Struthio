# Minimal Debian installation and startup

November 3, 2026 · America/Phoenix · written for HATCH SERVICE-01, startup and installation readback revised in HATCH INTEGRATION-01, words and packaging brought to Graphite 0.1 on November 6, 2026. Graphite is the public name of the program (earlier Ledger & Slate); the scripts, the installer file INSTALL_LS.py and the state folders keep their earlier names.

The product goal is a minimal Debian edition whose main visible workspace is Graphite. It should install from prepared USB media or pull a verified public release and its prerequisites over a working wireless connection. The current deliverable adds the application installer and a dedicated session launcher for an existing Debian system. A bootable Debian installer image, public release hosting and a complete offline dependency cache remain separate deployment work.

## What starts Graphite

The target is Debian 13 on the owner's AMD ThinkPad. No GNOME or KDE session is required. Python 3.11–3.13, the declared Qt runtime, display/input drivers and the existing programme dependencies are required. The dedicated session adds Xorg, xinit/startx, Fluxbox and a session bus. The optional minimal-session package group also includes NetworkManager and Mesa prerequisites.

From a local Debian text login, run `bash START_MINIMAL_DEBIAN.sh` in the installed programme. It checks the session commands (`startx`, `fluxbox`, `dbus-run-session` and an X server, `Xorg` or `X`) and calls startx with the supplied LS_XSESSION.sh. That session starts Fluxbox without its toolbar/slit and opens the Office fullscreen. Exiting Graphite ends this dedicated graphical session and returns to the text environment. From an existing display it opens the fullscreen Office without starting a second X server. Normal `bash START_OFFICE.sh` remains available.

From a text login the script takes no arguments: `--doctor`, `--version` and similar options belong to `bash START_OFFICE.sh`, or to START_MINIMAL_DEBIAN.sh from an existing display, where they are forwarded. Starting a whole X session to answer `--version` would be untruthful, so the text-login branch refuses arguments with a message instead.

Exit-status readback. xinit discards the session client's exit status and startx returns xinit's, so a plain `exec startx` would return 0 whether Graphite exited cleanly, crashed or never showed a window. LS_XSESSION.sh therefore runs START_OFFICE.sh once in the foreground, records `{"status":N,"utc":"…","log":…}` in `${XDG_STATE_HOME:-$HOME/.local/state}/ledger-slate/last-session.json` (naming `launch-error.log` only when one was written during that session) and exits with N; a failure to write the record never changes the exit status. START_MINIMAL_DEBIAN.sh removes the previous record before startx, reads the new one afterwards and prints one line, `Graphite ended with status N` (with `details: <launch-error.log>` when there is one) and exits with N, or `Graphite session ended; status not recorded (startx returned N)` when nothing was recorded. The session client's INT, TERM and HUP traps record 130, 143 and 129 the same way. A failed start writes its traceback to `${XDG_STATE_HOME:-~/.local/state}/ledger-slate/launch-error.log` (falling back to the folder beside the programme), prints it to the terminal, and the message names only a log file that was actually written.

LS_XSESSION.sh exports `ARC_LEDGER_FULLSCREEN=1` and `ARC_LEDGER_XSESSION=1`. The second marker is how the System menu (the pale Graphite symbol at the upper right; `workbench/system_menu_qt.py`, the words in `workbench/session_power.py`) knows it is running in the dedicated session: its leave row reads Return to Debian in this session and Exit Graphite from an existing desktop; it closes Graphite the ordinary way. The same separated group holds Log out, Restart and Shut down (HATCH DESK D2, the owner's brief): each first asks the leave flow's questions, asks for confirmation naming its scope (nothing is stopped before it), closes Graphite the ordinary way, then asks logind itself (`loginctl terminate-session`, `systemctl reboot` or `systemctl poweroff`, never sudo); logind's CanReboot and CanPowerOff decide whether they are offered. This session starts no permission agent, so where logind would ask for permission (`challenge`) Restart and Shut down read unavailable here and say to use `systemctl reboot` or `systemctl poweroff` at the text login after Return to Debian. START_MINIMAL_DEBIAN.sh's existing-display branch exports only the fullscreen marker, so an existing desktop reads Exit Graphite. Nothing in these scripts restarts Graphite: when it exits, the X session ends and the text login returns.

The scripts do not rewrite login files, enable automatic login, partition a disk, change Wi-Fi credentials or reboot the computer. Native display, input, driver and owner comfort checks remain open until the actual host is available. A later appliance edition needs an explicit tested automatic-start policy and recovery path.

## Using the supplied ZIP volumes

Download every numbered ZIP (`Graphite_0.1_part_NN.zip`), RELEASE_PARTS.json and INSTALL_LS.py (the Graphite installer; its file name is kept) into one directory. Every ZIP is at most 15,000,000 bytes. They are inspectable ZIPs containing ordinary project files, with hashed chunks only for a runtime archive too large to fit in a single volume. The installer validates that chunk inventory before writing anything and restores the file automatically before checking the full payload. Do not treat a single volume as a complete programme.

First review a plan:

```bash
python3 INSTALL_LS.py --usb . \
  --target "$HOME/Applications/Graphite_0.1" \
  --minimal-session --plan
```

The plan writes and downloads nothing. With `--extract-only` it lists the single extraction step and no start command, because extraction installs nothing.

For a USB programme with public dependency downloads over an already working connection:

```bash
python3 INSTALL_LS.py --usb . \
  --target "$HOME/Applications/Graphite_0.1" \
  --minimal-session --yes
```

Use `--profile suite` to select the existing engineering, worker, math and experiment dependency groups. Desktop is the smaller default. Exact model files, licences, native tool/runtime profiles and their qualification remain separate. No model download or native acceptance trial is initiated by this installer.

Use `--extract-only` to verify and restore the complete project without invoking sudo, apt or pip. Target a folder on the computer, not the media:

```bash
python3 INSTALL_LS.py --usb . \
  --target "$HOME/Applications/Graphite_0.1" --extract-only
```

The installer stages the programme in a hidden temporary folder beside the target and moves it into place in one step, so the folder that will contain the installation must be writable; a read-only USB folder is refused with a message naming that folder before anything is written, and FAT or exFAT media, which cannot hold the programme's file permissions, stops the staging with a message that says so (the staging is removed and nothing is installed; choose a folder on the computer). A refused or failed installation removes any empty parent folders it created and leaves no staging behind. An existing target folder is retained; choose a new release folder. Working records remain outside the replaceable programme under their established paths. A failed dependency installation retains the verified extracted programme for inspection and says so.

`--manifest-sha256` pins RELEASE_PARTS.json for USB media too, not only for public downloads: pass the checksum from a trusted source when someone else copied the media and the installer refuses a manifest that does not match it.

What the installer says at the end. `--yes` is passed to INSTALL_DEBIAN.sh only when you gave it. Without `--yes`, the sudo prompt needs a terminal; when none is attached the installer says so before it starts, INSTALL_DEBIAN.sh skips the apt step and exits 3 with the line `PREREQUISITES_SKIPPED` after the runtime installer succeeded, and the final line reads it back. The final line always names what happened, for example `Program extracted and verified · Runtime imports verified · Debian prerequisites skipped (no --yes and no terminal for the sudo prompt) · Minimal session prerequisites missing (startx, Xorg) · Owner display and native/model qualification remain separate.` A start command is printed only when it would work: when the minimal-session commands are missing the installer prints the desktop start line and the INSTALL_DEBIAN.sh command that installs them instead of `bash START_MINIMAL_DEBIAN.sh`. Every refusal reads `Installation needs attention: …` on standard error; a damaged manifest, chunk inventory or ZIP is a refusal, not a traceback.

## The optional packet capture

Log's Network stream (the writing line in Log mode) shows this computer's interfaces and connections without any extra package. Its packet capture runs the system's own capture tool, which a minimal Debian does not have. To add it, run `bash INSTALL_DEBIAN.sh --network-capture --yes` from the installed programme (INSTALL_LS.py does not pass this option; it is a separate, deliberate choice). It installs `wireshark-common`, which provides `dumpcap`, and nothing else: no Wireshark window, no group change.

Debian asks during that installation whether non-superusers should be able to capture packets. Answer Yes. Then the steps, in the words Log's Network stream uses (the administrator is root):

1. only if it did not ask, or you answered No: as the administrator, `dpkg-reconfigure wireshark-common`, and answer Yes: non-superusers may capture packets;
2. as the administrator, `usermod -aG wireshark <your login>`;
3. log out and in again, so the session carries the wireshark group.

The installer prints these steps, worded the same way and with your login, instead of running them. Graphite itself never runs them, never asks for the administrator's password and never changes the system's permissions: when capture is not possible, Log's Network stream says why and lists the same steps. What a capture keeps (header fields only: the capture tool passes at most 128 bytes of each packet, which after short headers include the first bytes of what the packet carries; Graphite's parser reads the header fields and drops the rest at once), that it is never in promiscuous mode and is bounded by seconds and packets, who may start one (only you; an assignment proposes and waits) and where its summaries live are in docs/NETWORK_01.md. Capture only networks you own or may monitor.

## Fully offline USB

A fully offline USB also needs OFFLINE_FILES.json and matching `debs/` and `wheels/` folders. This cache is not contained in the programme parts. Prepare it on a clean target-matching Debian environment so already installed dependencies are not accidentally omitted. Include all transitive system dependencies needed by the chosen profile and wheels for its exact architecture and Python version.

The inventory schema is `ledger.offline-files/1`. Its `files` object maps each relative path under debs or wheels to byte count and SHA-256. Unlisted files, missing wheels and changed dependencies are refused. The installer invokes apt with `--no-download` for supplied Debian packages and the existing runtime installer with pip `--no-index` for supplied wheels. Missing prerequisites fail rather than falling back to a network download.

```bash
python3 INSTALL_LS.py --usb /media/USB \
  --target "$HOME/Applications/Graphite_0.1" \
  --offline --minimal-session
```

The base Debian installation, wireless/display firmware and account setup must already be usable. Model weights remain separate, as do any external native runtime assets that the selected profiles require. The eventual bootable appliance USB should guide these base-system steps, but this checkpoint does not supply such an ISO.

## Public release download

The installer supports `--public-manifest` with a public HTTPS RELEASE_PARTS.json URL and mandatory `--manifest-sha256`. ZIP names are resolved relative to that manifest. It verifies transport sizes, ZIP hashes, restored chunks and the complete payload before running an installer. TLS verification stays enabled. No downloaded script is piped directly into a shell. The downloaded parts (about 77 MB) are held in the system temporary folder, which is a memory-backed tmpfs on Debian 13, until extraction completes.

A public Graphite release has not been published yet. Use a real published URL and its separately trusted checksum when hosting is established. The supplied private review links are not public release hosting. Programme checksums establish integrity relative to the supplied manifest, not publisher identity by themselves.

Wireless download requires a working connection before installation starts. Debian may require firmware for the actual wireless hardware. Use the official Debian installer/firmware route or a matching offline cache; no assumption is made about the exact ThinkPad wireless chip. No OS package installation, wireless configuration or X session has been run on the owner host in these cloud checks.

## Packaging the volumes

Two steps, both from the program folder. `python3 tools/package_graphite.py OUT` rebuilds the seed (`project/stacy_seed/current`, the program's own sources for staC), rewrites `MANIFEST.json` (`graphite_release` 0.1, `version` from `workbench/version.py`, every shipped file with its size and SHA-256) and writes `OUT/Graphite_0.1_full.zip`; `--dry-run` writes nothing and lists what would be shipped and how the manifest would change, `--manifest-only` rewrites only the seed and the manifest. From `build/` only Graphite 0.1's own evidence (`build/graphite01_ui`) and the live model-trial records (`build/agent01_ui/model_trial`, `build/agent02_ui/model_trial`) are shipped; what the Qt checks write there when run by hand stays local. Then `python3 tools/package_release_parts.py OUT/Graphite_0.1_full.zip PARTS_FOLDER "Graphite 0.1"` writes the volumes `Graphite_0.1_part_NN.zip` and RELEASE_PARTS.json. The release name is a required argument; the tool carries no default that could label a new release with an old name. The first volume carries the entry points (INSTALL_LS.py, the start and install scripts, MANIFEST.json), README.md, RECORD_OF_DIRECTIONS.md, the daily guide, this note and the complete specification. `tests_integrated/test_install_media.py` packages a fixture archive with small volume and chunk limits and restores it through the shipped installer, checking bytes and file modes.

## Quick installation and later acceptance

The new entry point selects `--quick`: install the declared dependencies, verify runtime imports, release integrity and source bindings, then show the startup commands. INSTALL_LEDGER.sh prints the `bash START_MINIMAL_DEBIAN.sh` line only when `startx`, `fluxbox`, `dbus-run-session` and an X server are present; otherwise it names the missing commands and the INSTALL_DEBIAN.sh command that installs them, and the Office start line stays. The original extended installer walkthroughs remain available when deliberately requested. Quick installation is not native, exact-model, protected-worker or owner-host acceptance.

Before appliance release, demonstrate a fresh Debian install, real display/input, a complete offline USB install, a public wireless install, actual GGUF inference, service cycling, recovery and an update preserving owner work. The complete project specification defines these acceptance requirements in detail.

Official sources checked November 3, 2026:

- [Debian installation guide](https://www.debian.org/releases/trixie/amd64/install.en.html)
- [Loading missing firmware](https://www.debian.org/releases/trixie/amd64/ch06s04.en.html)
- [xinit and startx](https://packages.debian.org/trixie/xinit)
- [Fluxbox manual](https://manpages.debian.org/trixie/fluxbox/fluxbox.1.en.html)
