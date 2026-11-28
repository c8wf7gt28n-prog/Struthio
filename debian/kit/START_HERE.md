# Kas @VERSION@: install it as Debian software

This kit installs Kas with `apt`, from a folder on your USB stick. It is made for a Debian 13 computer that
already has the Kas 1.0 System set (the packages the 1.0 kit installed). Nothing here needs the network.

It goes in **two stages**. Stage 1 changes nothing about how the computer starts: you still log in on the text console
and start Kas with one command. Stage 2, the graphical login screen, is optional and separate, because a login
screen changes how the computer boots. Do stage 2 only after stage 1 works.

## Your Kas 1.0 stays

If you have `~/Applications/Graphite-1.0`, leave it. The new Kas opens the same workspace (`~/Concern/Office`) and
the same settings; nothing is moved or copied. To go back at any time, start the old one as before:
`bash ~/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh`. To take the new one away, see "Going back" below.

## 0. Put the kit together (as your ordinary user)

Copy every file of the kit into one folder on the stick or in your home, for example `~/KasKit`. Then:

    cd ~/KasKit
    bash JOIN.sh

It checks every file by sha256, unpacks the ZIPs into `repo/` and joins the large files from their pieces. It ends
with `JOINED AND CHECKED`. If it says a file does not match, copy that file again and run it again.

## 1. Stage 1: Kas and its session (the text console way, as before)

Become root and look first (this changes nothing):

    su -
    bash /home/YOU/KasKit/install.sh --check

Then install:

    bash /home/YOU/KasKit/install.sh

It copies the repository to `/var/lib/graphite-kit/repo`, adds it as an apt source and runs
`apt-get install kas-computer kas-session`. Type `exit` to leave root. Log out and in again on the text console (the
session services need a fresh login), then start Kas exactly as before, with one command:

    kas-startx

Check it from a terminal at any time: `kas-computer --version`, `kas-doctor doctor`.

**Already installed from an earlier 1.1 kit?** The packages were called `graphite`, `graphite-session`,
`graphite-llama-runtime` and `graphite-desktop`; they are now `kas-computer`, `kas-session`, `kas-llama-runtime` and
`kas-desktop`. The same `install.sh` (or `apt upgrade` once the kit's source is in place) moves you across: each old
package becomes a small transitional one that pulls in its new name, and may be removed afterwards
(`apt remove graphite graphite-session graphite-llama-runtime graphite-desktop`). The old commands (`graphite-startx`,
`graphite-do` and the others) still work for one release and say their new name.

## 2. Stage 2, optional: the graphical login screen

Only when stage 1 works. As root:

    bash /home/YOU/KasKit/install.sh --desktop

This installs `kas-desktop`: LightDM's login screen, set to start the Kas session. At the next boot you log
in on the login screen instead of the text console.

**To undo it**, two commands, as root:

    systemctl disable lightdm
    apt remove kas-desktop lightdm lightdm-gtk-greeter

**If the login screen does not come up** after a reboot: press Ctrl+Alt+F2 for a text console, log in as root, type
`systemctl disable --now lightdm`, then log in as your user and type `kas-startx`. Kas starts as in stage 1.

## Going back

- Remove the new Kas (as root): `apt remove kas-computer kas-session kas-llama-runtime kas-desktop`.
  Your workspace in `~/Concern`, your settings in `~/.config/arc1-workbench` and `~/.local/state/ledger-slate` stay.
  Your old `~/Applications/Graphite-1.0` keeps working.
- Remove the kit's apt source and its copy (as root): `bash install.sh --forget`.

## What this preview is and is not

- The packages are not signed with a Kas release key yet; the release key is the owner's to make and keep. The
  kit's apt source is marked trusted and every file is checked by sha256 (`SHA256SUMS`, `PIECES.sha256`,
  `KIT.sha256`), and apt checks every package against the repository's index.
- Tried in the build container: the packages build; from these ZIPs alone (joined and checked), `apt install kas-computer
  kas-session` succeeds in a fresh Debian 13 chroot that has the 1.0 System set's packages; `kas-computer --check`
  passes as an ordinary user with nothing written under `/usr`; `apt remove kas-computer` leaves the workspace.
- Not tried there, and only your computer can show it: the login screen itself, the session under it, Wi-Fi and sound.
