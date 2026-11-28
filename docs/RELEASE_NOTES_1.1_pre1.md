# Graphite 1.1 preview 1: installs like Debian software

*28 November 2026. The first of four previews on the way to Graphite 1.1, the distribution candidate. A preview is sent
the moment its work is merged, so you can test what is ready without waiting for the rest. Previews 2, 3 and 4 follow
the same way.*

## What is new

**Graphite installs as Debian software.** Graphite now comes as four Debian packages in a folder repository:

- **graphite**: the program in `/usr/lib/graphite`, running on Debian's own PySide6.
- **graphite-llama-runtime**: the bundled llama.cpp, for Kas's model.
- **graphite-session**: the X session entry, plus `graphite-session`, `graphite-startx` and `graphite-do`.
- **graphite-desktop**: optional; it adds a LightDM login screen.

To install, copy every file of the kit into one folder and run `bash JOIN.sh` as yourself. It checks every piece and
ends with `JOINED AND CHECKED`. Then, as root (`su -`), run `bash install.sh --check` to look first, and `bash install.sh`
to install. That is `apt-get install graphite graphite-session` from the folder. Log out and back in on the console,
then start Graphite with `graphite-startx`, as before.

For the login screen as well (stage 2, only once stage 1 works), run `bash install.sh --desktop` as root. Two commands
undo it, and `START_HERE.md` has them, along with what to do if the login screen does not come up.
Your `~/Applications/Graphite-1.0` and your workspace stay where they are, and `START_HERE.md` also says how to go back
to 1.0. `apt remove graphite` removes the program and never touches your files.

**A Windows hand's keys, everywhere.**

- **In Files:**
  - Ctrl+C, Ctrl+X and Ctrl+V copy and move files, with one Undo per paste.
  - F2 renames, and Delete puts things in the bin.
  - Shift+Delete asks first, then deletes for good.
  - Enter opens, Alt+Enter shows Properties, F5 reads the folder again, and Backspace goes back.
- **Above every app in the Graphite session:**
  - The Windows key opens Apps.
  - Win+E opens Files, Win+D brings Graphite forward, and Win+L locks.
  - Ctrl+Alt+Del shows what runs, and PrintScreen saves a picture into `Pictures/Screenshots`.
  - Alt+Tab and Alt+F4 work.
- **On screen:** menus show their keys again (Rules ▸ Show keys turns them off). The dock has a clock; press it for the
  month.

**DOS words in the Terminal.**

- `dir`, `cd..`, `copy`, `move`, `del`, `ren`, `md`, `type`, `cls`, `ipconfig` and more work. Each shows the Debian
  command it ran, so the bridge teaches itself away.
- `del` goes to the bin with Undo, and `copy` and `move` never write over a file without `/y`.
- `format` and `chkdsk` are explained, never run.
- Rules ▸ DOS words sets on, show me only, or off.

**The test tiers, made to run again.** 1.0 was merged with no test run, as you asked. Preview 1 made the test tiers
run again. They found 11 real faults, and all are fixed. One was a crash: a tab's icon was freed while Qt still painted
it. Others were wrong names at Kas's door to the desk and Apps too narrow in Day. About 14 tests were moved to what 1.0
decided. In the Graphite look, tier 2 went from 60 failing to 23 before the last fixes. The whole tiers were not run
again after them, and the Kasandra and Night looks were not run.

## What was tested, and what was not

You allowed minimal tests for 1.1:

- Each piece of work has its own small test file.
- At each merge the seed was rebuilt and the window opened offscreen in all four looks: Graphite, Kasandra, Day and
  Night.
- The packages were built and checked with dpkg-deb and lintian, and installed in a clean Debian 13 chroot that held
  the 1.0 System set.

These have **not** been exercised here, because the build machine has no screen:

- the LightDM login screen;
- the keys through a real Fluxbox (the key helper was called directly);
- anything on your ThinkPad.

## What preview 1 does not do yet

- There is no signed repository: the folder is marked trusted and checked by checksums. The release key is yours to
  make and keep.
- No man pages, no "safe start" session entry, and no in-app updater words for a dpkg-owned install.
- There is no Guide page for the keys or the DOS words yet.
- The test tiers are not yet at zero failing: the rest is in preview 2.
- Kas's sharper voice (KV) moved to preview 2.
- Preview 2 brings one bar along the bottom above every app (Start, the line, the windows, Kas with HALT, the tray, the
  clock), the Explorer (Quick access, List, Icons and Board views) and File/Edit/View/Go/Tools/Help menus.

## Reversals for you to strike

These go against decisions you made earlier. Each is the builder's call for a distribution, and yours to strike: say
"strike N" and it goes back.

| # | Earlier decision | In 1.1 | Why | Preview |
|---|---|---|---|---|
| 1 | No key printed on screen (13 Nov) | Keys shown in menus and tips; one setting turns them off | a person switching learns keys from menus | pre1 |
| 2 | Text console start only | A graphical login as well; the console start stays | a distribution boots to a login | pre1 |
| 3 | HALT upper left (26 Nov) | HALT on the bar beside Kas's name | an app in front hides the head; the bar is above every app | pre2 |
| 4 | Apps upper right (14 Nov) | Start at the lower left, on the Windows key; the word stays "Apps" | where a Windows hand goes | pre2 |
| 5 | The tree from "This computer /" (26 Nov) | Quick access first, the root one press down | 1.0's first sight was system folders | pre2 |
| 6 | DELETE as the bin's word (14 Nov) | "Recycle Bin" on new installs; your profile keeps DELETE | a capital verb reads as an act | pre2 |
| 7 | The eight menus' names | File, Edit, View, Go, Tools, Help over the same actions | the names a Windows hand knows | pre2 |
| 8 | "Outside your home: never" for Kas | System changes through the system's own prompt, you present | a full Linux box means software and services | pre3 |

Not reversed: no picture of Kas; Apps, never Programs; Day as the launch look; every state a word and a shape.

## Your test, if you have twenty minutes

1. Copy the kit's files into one folder (for example `~/GraphiteKit`). Run `bash JOIN.sh` (it ends `JOINED AND
   CHECKED`). Then, as root (`su -`), run `bash ~/GraphiteKit/install.sh --check`, then `bash ~/GraphiteKit/install.sh`,
   writing your own home folder in place of `~`.
2. Log out of the console and back in, then run `graphite-startx`. Graphite should open as 1.0 did, with the clock on
   the dock.
3. In Files, in a scratch folder: Ctrl+C a file, Ctrl+V it, Ctrl+Z. Press F2, Delete, then Shift+Delete on a copy.
   Alt+Enter shows Properties.
4. With LibreOffice in front, press the Windows key, then Win+E, Win+D, Alt+Tab and PrintScreen.
5. In the Terminal, type `dir`, `cd..`, `ipconfig` and `del` on a scratch file; then Undo.
6. Optional: as root, `bash ~/GraphiteKit/install.sh --desktop`, then reboot to the login screen and choose
   Graphite.

Whatever differs from the page is a result. Send it, with a photo if it's on screen.
