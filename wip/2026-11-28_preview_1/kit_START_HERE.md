# Graphite 1.1~pre1: install it as Debian software

This kit installs Graphite with `apt`, from a folder on your USB stick. It is made for a Debian 13 computer that
already has the Graphite 1.0 System set (the packages the 1.0 kit installed). Nothing here needs the network.

It goes in **two stages**. Stage 1 changes nothing about how the computer starts: you still log in on the text console
and start Graphite with one command. Stage 2, the graphical login screen, is optional and separate, because a login
screen changes how the computer boots. Do stage 2 only after stage 1 works.

## Your Graphite 1.0 stays

If you have `~/Applications/Graphite-1.0`, leave it. The new Graphite opens the same workspace (`~/Concern/Office`) and
the same settings; nothing is moved or copied. To go back at any time, start the old one as before:
`bash ~/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh`. To take the new one away, see "Going back" below.

## 0. Put the kit together (as your ordinary user)

Copy every file of the kit into one folder on the stick or in your home, for example `~/GraphiteKit`. Then:

    cd ~/GraphiteKit
    bash JOIN.sh

It checks every file by sha256, unpacks the ZIPs into `repo/` and joins the large files from their pieces. It ends
with `JOINED AND CHECKED`. If it says a file does not match, copy that file again and run it again.

## 1. Stage 1: Graphite and its session (the text console way, as before)

Become root and look first (this changes nothing):

    su -
    bash /home/YOU/GraphiteKit/install.sh --check

Then install:

    bash /home/YOU/GraphiteKit/install.sh

It copies the repository to `/var/lib/graphite-kit/repo`, adds it as an apt source and runs
`apt-get install graphite graphite-session`. Type `exit` to leave root. Log out and in again on the text console (the
session services need a fresh login), then start Graphite exactly as before, with one command:

    graphite-startx

Check it from a terminal at any time: `graphite --version`, `graphite-doctor doctor`.

## 2. Stage 2, optional: the graphical login screen

Only when stage 1 works. As root:

    bash /home/YOU/GraphiteKit/install.sh --desktop

This installs `graphite-desktop`: LightDM's login screen, set to start the Graphite session. At the next boot you log
in on the login screen instead of the text console.

**To undo it**, two commands, as root:

    systemctl disable lightdm
    apt remove graphite-desktop lightdm lightdm-gtk-greeter

**If the login screen does not come up** after a reboot: press Ctrl+Alt+F2 for a text console, log in as root, type
`systemctl disable --now lightdm`, then log in as your user and type `graphite-startx`. Graphite starts as in stage 1.

## Going back

- Remove the new Graphite (as root): `apt remove graphite graphite-session graphite-llama-runtime graphite-desktop`.
  Your workspace in `~/Concern`, your settings in `~/.config/arc1-workbench` and `~/.local/state/ledger-slate` stay.
  Your old `~/Applications/Graphite-1.0` keeps working.
- Remove the kit's apt source and its copy (as root): `bash install.sh --forget`.

## What this preview is and is not

- The packages are not signed with a Graphite release key yet; the release key is the owner's to make and keep. The
  kit's apt source is marked trusted and every file is checked by sha256 (`SHA256SUMS`, `PIECES.sha256`,
  `KIT.sha256`), and apt checks every package against the repository's index.
- Tried in the build container: the packages build; from these ZIPs alone (joined and checked), `apt install graphite
  graphite-session` succeeds in a fresh Debian 13 chroot that has the 1.0 System set's packages; `graphite --check`
  passes as an ordinary user with nothing written under `/usr`; `apt remove graphite` leaves the workspace.
- Not tried there, and only your computer can show it: the login screen itself, the session under it, Wi-Fi and sound.
