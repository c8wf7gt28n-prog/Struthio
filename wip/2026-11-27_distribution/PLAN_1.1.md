# Graphite 1.1 — the distribution candidate, in previews

*28 November 2026. The source every 1.1 builder's brief is made from. It replaces nothing in 1.0; it builds on it.*

## 1. The mandate (the owner, 27 and 28 Nov 2026, verbatim)

- "this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos. But I know I can only get what
  I want in Debian so I have to switch. If I lift all rules and allow minimal tests, do you think you can make it fully
  distribution ready?"
- "Feel free to change anything under the hood and anything visible. Think the functionality of windows, with the
  graceful class of Apple, and the freedom power of Linux"
- "Kasandra is the "super power" of this project. Make her very useful at everything in a world where a full loaded
  Linux box is the computer I use."
- "Kasandra is like Kate Libby (from hackers movie) :)"
- "Save your work often to survive usage resets" · "Save every 5 minutes and or at milestones"
- "Can you take into consideration my weekly limit and release what you can if it's not finished. So I don't have to
  wait several days to finish, before I test what I can?"

## 2. How 1.1 is built: previews, lean

- **Previews.** 1.1 arrives as numbered previews (1.1-pre1, pre2, …). Each is a whole, installable kit the owner can
  test the same evening. **The rule: whenever a preview's slices are merged, cut it and send it at once. If a usage
  limit stops the build for long, cut what is merged and send that.** Nothing waits for the whole.
- **Lean.** The owner has a weekly usage limit. No fan-out panels. At most three builders at once, each one slice, on
  the Opus model (it built 1.0); the coordinator decides designs itself from what the 27 Nov panels left
  (`wip/2026-11-27_distribution/partial/`). Builders read only what their slice names.
- **Tests are allowed, and minimal.** Each builder adds a small test file for what it builds and runs only its own tests
  and the ones it touches. The tiers are run by the coordinator as a plain job (no agent).
- **Kept by the builder's own choice:** the owner's details and pictures never enter the repository; Kas's authority
  rules (the model proposes, the desk disposes; every change waits for the owner's press or a grant in plain words; a
  step is done only when verified; HALT); tests and the app run only on throwaway copies; the branch
  `claude/epic-galileo-c7k11y` only; commit and push after every step; save every 5 minutes
  (`wip/build_tools/save_dist.sh loop`).
- **Reversals of the owner's earlier explicit decisions** are allowed by the brief and are listed in each preview's
  notes for the owner to strike (section 6).

## 3. What "distribution candidate" means (checkable)

1. `apt install graphite-desktop` from a folder on a stick installs everything; `apt remove` leaves the user's work.
2. Power on → a graphical login → Graphite. The text console start stays as a second way.
3. A Windows-and-DOS person's keys and words work (section 6 of the design direction); DOS commands work in the
   Terminal and show the Debian command they ran.
4. One bar above every app: Start, a line that finds and does, the open windows, Kas with HALT, the tray, the clock.
5. Files behave as an Explorer (columns, sort, cut/copy/paste, Properties) and still open the bulletin board.
6. A Control Panel covers software and updates, printers, Bluetooth, date and time, users, power, displays, sound,
   network, default apps; a Task Manager shows processes and Kas's work.
7. Kas does real work on the whole box: verified recipes for everyday tasks, any command through a classifier
   (reads sealed, changes on the owner's press, system changes through the system's own prompt), grounded in the
   machine's own manual pages, and she teaches Debian in DOS and Windows words.
8. Her voice: sharp, sure, dry, never bluffing.
9. The existing test tiers pass, and the authority code has its own minimal tests.
10. It runs on machines that are not the ThinkPad (other screens, no Radeon, 8 GB).
11. The old rooms that 1.1 replaces are gone or behind one "Engineering tools" switch; no old name shows on screen.
12. Licences are complete for redistribution; the package excludes what RIGHTS.md keeps back.
13. A live image boots to "Try Graphite / Install Graphite" (if this machine can build one; a QEMU boot smoke).

Only real machines give the final word: the login screen, the global keys under Fluxbox, suspend, Wi-Fi, Bluetooth,
printers, the Radeon and the 35B.

## 4. The previews

| Preview | Name | Slices | Gives the owner |
|---|---|---|---|
| **pre1** | Installs like Debian software | PK1, T1, W1, KV | apt packages and a graphical login; the tiers green; Windows keys and DOS words; her voice |
| **pre2** | One bar | B1, B2, B3, E1, K0 | the bottom bar with Start, the line, tray and clock; Explorer view and Properties; Kas on the bar with HALT |
| **pre3** | Kas reaches the box | KS1, KS2, KS3, KS4 | recipes, the command tool, the system door, manual-page grounding and "teach me" |
| **pre4** | The Control Panel | C1, C2, C3 | software and updates, printers, Bluetooth, time, users, power; the Task Manager |
| **1.1** | The candidate | Z1, Z2, Z3, Z4 | the live image, the security and licence reviews, old rooms cleared, the walk and the docs |

*28 Nov 07:20: as built so far: pre1 = PK1, W1, T1; pre2 = B1, E1, KV, B2, K0, B3; pre3 = KS1, B4, T2 (KS2 and KS3 were
stopped by a usage limit and moved); pre4 = KS2, KS3, KS4, a real terminal, C1-C3; 1.1 = Z1-Z4.*

## 5. The slices

### Preview 1 — installs like Debian software

**PK1 · Debian packages and a graphical way in.** From the packaging audit (read
`wip/2026-11-27_distribution/partial/packaging/NOTES.md` sections 5, 7 and 10 first; its trial `build_deb.sh` is in
scratch at `$S/work/dist/packaging/` and, if scratch is gone, described in the notes). Build: a `debian/` tree and
`tools/build_deb.sh` giving `graphite` (all: `/usr/lib/graphite`, `/usr/bin/graphite`, a desktop entry and icon; Depends
on Debian's own python3, python3-pyside6.* and the libraries the 1.0 System set names), `graphite-llama-runtime` (amd64:
the bundled llama.cpp archives, so `graphite` stays small), `graphite-session` (`/usr/share/xsessions/graphite.desktop`
with `Exec=graphite-session`, the supervisor and Fluxbox files, and `graphite-startx` for the text console) and
`graphite-desktop` (a meta package: Recommends lightdm and lightdm-gtk-greeter with `user-session=graphite`, firmware
only as Recommends). `tools/build_repo.sh` makes a folder repository (Packages, Release) with the dependency closure
downloaded in a clean Debian 13 chroot **against a ThinkPad that already has the 1.0 System set**
(`wip/build_tools/kit_1.0/SYSTEM_SET_1.0.json`, as R1 simulated: `wip/2026-11-26_b100_saved/R1.progress.md`), and
`tools/build_kit.sh` packs it as ZIPs each under 15,000,000 bytes (a file larger than that is split and joined by
`JOIN.sh` on the stick, every piece checked by sha256) with an `install.sh` that adds the folder as an apt source and
runs `apt install`. The doctor and the readiness check accept Debian's own versions (PySide6 6.8.2.1) instead of exact
wheel versions. A user who has `~/Applications/Graphite-1.0` keeps it and their workspace; the page says how to go back.
**The release key is the owner's to make and keep:** previews use a local folder source marked trusted and checked by
checksums; `build_repo.sh --sign-with KEYID` signs when a key exists. *Acceptance:* the packages build here; from the
kit's ZIPs alone (joined, checked) `apt install graphite graphite-session` succeeds in a fresh Debian 13 chroot that
has the 1.0 System set's packages; `graphite --check` passes as an ordinary user with nothing written under `/usr`;
`apt remove graphite` leaves a workspace in the user's home; lintian's errors are answered or listed. Not checkable
here, and said so: the login screen itself.

**T1 · The tiers green.** The 1.0 slices were merged with no test run. A run on 27 Nov (in scratch:
`$S/work/dist/tests/tier0/tier0.json`, `tier2_default/tier2.json`, `tier2_default/cluster.txt`, logs beside them; the
summary is in `wip/2026-11-27_distribution/partial/tests/`) gave: tier 0, 9 failing of 435; tier 2 in the Graphite look,
60 failing of 1,264 in 27 units, among them `test_desk_acts` dying with exit -11 ("This plugin does not support grabbing
the keyboard"), `test_one_name` finding "Stacy" on screen, seven window checks (`tools/check_*_ui.py`), `FakeLogind`
lacking a method the leave flow now calls, tests that still expect the foot's mode to be called `slate`, the playable
scene P01 on Rail Demo, and the resource rules. For each failure decide: the test asserts a truth 1.0 changed on purpose
(update the test to the new truth and say which slice changed it), or the program is wrong (fix the program), or the
environment lacks something (make the test say so plainly; never skip a test to get green). Add the Day and Night looks
to the tier runner's looks. *Acceptance:* tier 0 and tier 2 in the Graphite and Day looks end with 0 failing on a copy,
the runs' JSON saved; a list of every real fault fixed, with its file; the keyboard-grab crash explained and fixed.
W1 (beside you) reverses "no key printed on screen": leave `test_one_name`'s key test to W1 and say so.

**W1 · A Windows hand's keys, and DOS words.** (a) In Graphite's window the keys a Windows hand uses without thinking:
Ctrl+C, Ctrl+X and Ctrl+V on files (a file clipboard over the tree and bulk selection, each paste one change with
Undo), F2 rename, Delete to the bin, Shift+Delete asking before deleting for good, Enter opens, Alt+Enter Properties (a
small page: name, kind, size, dates, where it is, who may read and change it in words, what opens it), F5 reads again,
Backspace and Alt+Left go back, Ctrl+A, Ctrl+F, Ctrl+S, Ctrl+Z and Ctrl+Y, Esc closes. (b) Keys that work whichever
app is in front, through Fluxbox's keys file written by the session and a small `graphite-do` command that speaks to the
running window over a local socket: the Windows key opens Apps, Alt+Tab goes to the next window, Alt+F4 closes the
window in front, Win+E opens Files, Win+D shows Graphite, Win+L locks, Ctrl+Alt+Del opens Graphite's page of what runs,
PrintScreen saves a picture of the screen into `~/Pictures/Screenshots` and says so. (c) Menus and tips show their keys
(this reverses the owner's rule of 13 Nov; one setting, "Show keys", turns them off; `test_one_name`'s key test moves to
the new truth). (d) A clock and the date at the dock's right end; a press shows a month. (e) **DOS words in the
Terminal** (`workbench/dos_words.py`): `dir`, `cd..`, `cd\\`, `cls`, `copy`, `xcopy`, `move`, `del`, `ren`, `md`, `rd`,
`type`, `more`, `tree`, `attrib`, `ver`, `date`, `time`, `set`, `path`, `echo`, `find`, `help`, `exit`, `ipconfig`,
`ping`, `tasklist`, `taskkill`, drive letters (`C:` is `/`, other letters are the mounted drives in order),
backslashes, and the common switches (`dir /s /b /a`, `del /q`, `copy /y`, `xcopy /s /e`). Each is translated to the
Debian command and **shown** on a line above its output ("dir /s → ls -lR"), so the owner learns; `del` goes to the bin
with Undo; `format` and `chkdsk` are explained, never run. One setting: DOS words on, off, or "show me only". *Acceptance:*
a smoke over 60 DOS lines giving the expected Debian command each; the file clipboard cutting three files and pasting
them with one Undo; the Fluxbox keys file and `graphite-do` exercised under Xvfb with the stand-in window manager where
possible, and said plainly where only Fluxbox on the ThinkPad can show it.

**KV · Her voice.** The owner: "Kasandra is like Kate Libby (from hackers movie) :)". Her manner, not a copy: sharp,
fast, sure of her craft, at home on the command line, dry wit, short sentences, no padding, never talks down, on the
owner's side. No line, name or handle from the film, and no picture. Rewrite `workbench/kasandra/character_starter.md`
(registers, manner, joining words, never-say, lengths: shorter) and every sentence the window says for her (her column,
"Waits for you", HALT and RESUME, grants, plans, refusals, the no-model line, empty states, toasts, the Guide's two
pages) in that voice, through the existing voice gate. **One guard:** she is sure only about what is verified; where
nothing is proven she says so just as plainly ("Not verified. Here is what I checked."). She never jokes about a
refusal, a loss or a permission. Tests that assert her exact words move to the new words. *Acceptance:* a table of 60
before-and-after sentences in the result; the voice sweep (`mind_words.check`) passes; no sentence over 20 words in the
plain register; frames of her column in Day at both sizes. Runs after T1 is merged.

### Preview 2 — one bar (outline; briefs are written when pre1 is cut)

**B1 · The bar.** One bar along the bottom of the screen, above every app, in its own X window like 1.0's dock
(`workbench/system_dock_qt.py`, `windows_strip_qt.py`, `windows_x11.py`): 44 px tall at 1920x1200, 40 at 1366x768,
reserving its space (a `_NET_WM_STRUT_PARTIAL` at the bottom, so Fluxbox and apps keep clear of it; the 1.0 dock at the
top goes). Named slots, left to right: **start** (a Start button; B2 fills it), **line** (a placeholder field; B2 fills
it), **windows** (the open app windows and Graphite, the active one marked, one press brings it forward, a right-click
minimises or asks it to close: 1.0's dock behaviour moved here), **kas** (a placeholder; B3 fills it), **tray**
(network, volume, battery as glyph plus word, each opening a small flyout above it with the Machine page's own actions:
`machine_real.py` and `net_meter.py` are read, never edited), **clock** (time and date; a press shows a month; W1 may have
added a clock to the dock: move it here). New `workbench/bar_qt.py` with `register_slot(name, widget_factory)` so later
slices fill slots without editing it; tokens from `design_tokens.py`. Inside Graphite's window nothing moves yet (the
foot and the head stay until K0). The design: `$S/work/dist/design/proposal_familiar.md` sections 2 and 5 (also in
`wip/2026-11-27_distribution/partial/design/`). *Acceptance:* under Xvfb with the stand-in window manager
(`wip/2026-11-26_b100_saved/S3.xworld.py`), the bar stands at the bottom with its strut set, lists two xterms and
Graphite, brings one forward, and the tray's three flyouts open; frames in Day and Night at both sizes; a test of
`register_slot`. **B2 · Start and the line.** The Windows key opens Start (apps by kind, recent, power); the line finds and
does everything (apps, files, settings, commands, sums, "Ask Kasandra"), and every row says what Enter will do.
**B3 · Kas on the bar.** Her chip (state word and shape), her panel sliding from the right edge over any app, permission
cards rising from her chip, HALT beside her name; her rules do not move. **E1 · Explorer.** The Files tree and the centre become an Explorer, with the
bulletin board as its third view. The navigation pane: **Quick access** first (Home, Desktop, Documents, Downloads,
Pictures, Music), then **the Desk** (the drawers of records), then **This computer** (the root one press down, drives
with letters and free space), then the bin. A folder opens in the centre in one of three views, switched on the
centre bar: **List** (a details view: Name, Modified, Type, Size, Links, sortable by a press on the column, with
multi-select as L6c built it), **Icons** (thumbnails for pictures), **Board** (1.0's bulletin board of the selected
thing). An address field in the centre bar takes a typed path. "Recycle Bin" is the bin's word on new profiles; a
profile that has used 1.0 keeps DELETE (a setting changes it). Builds on `computer_tree_qt.py`, `home_files_qt.py`,
`files_qt.py`, `bulk_files_qt.py`, `trash_can_qt.py`, `centre_one_qt.py`; new `explorer_qt.py`; W1's Properties page
and file clipboard are used, not rebuilt. Not `board_qt.py`'s drawing. The design:
`proposal_familiar.md` section 4. *Acceptance:* the everyday Home opens on Quick access; Downloads in List view sorts by
size and date; a picture folder in Icons view shows thumbnails; Board view of a sheet shows 1.0's board; a typed path
opens; frames in Day at both sizes. **K0 · The frame.**
The head's menus as File, Edit, View, Go, Tools, Help over the same actions; the details pane; tokens 1.1.

**T2 · The tiers green again, and the words to match.** Everything merged since T1 changed truths the tiers test:
the bar (B1), the Explorer opening on Quick access with Recycle Bin (E1), her voice (KV), Start on the Windows key
(B2), the six menus, a 32 px head and 115 px of chrome (K0). Run tier 0 and tier 2 on a copy of the tree in Day (the
launch look) and Graphite, then Night and Kasandra as time allows; fix real program faults; move tests to the new
truths and list each move; finish T1's open list (T1.build.result.json not_done). Sweep the docs and the Guide for
the old menu names (head_menus.MOVED gives old -> new), the dock, "Apps upper right" and DELETE where a new profile now
says Recycle Bin. *Acceptance:* tier 0 and tier 2 at 0 failing in Day and Graphite, or every remaining failure named
with its cause; no doc names a menu that no longer exists.

### Preview 3 — Kas reaches the box (outline)

**B4 · One line, a drop-down Terminal, and Command….** The window's foot (Line, Terminal, Search, Web, Log and the
meters) and the bar's line now do one job twice; one place for each thing. The foot folds away: the bar's line takes
Line, Search and Web; the Terminal becomes a real shell that drops from the top edge of the screen on one key (Win+`,
and Ctrl+Alt+T) over any app, understands DOS words (W1) and leaves when done; Log and the meters find one home each
(an old -> new table, as K0's). "Command…" above Properties on the right-click of a file or a tile shows the exact line
it is or runs, with Copy and "Put it in the line". Win+K opens her panel and Pause presses HALT from any app
(graphite-do verbs). *Acceptance:* no foot in Graphite's window; everything the foot did is reachable, each in one
place; the Terminal drops over an xterm and back; Command… on a file shows its line; Win+K and Pause work from an app.

**KS1 · Recipes.** A library of verified, parameterised recipes (preconditions, steps through registered tools, a dry
run, a verifier, an undo), forty to start: find big files, free space, convert and resize pictures, merge and split
PDFs, zip and unzip, back up a folder, what changed since yesterday, rename many, what uses memory, is the system up to
date. With no model her dictionary picks; with one, the model picks by number and fills slots only from the owner's
words. **KS2 · The command tool.** Any command as argv, never a shell string, through a classifier that knows which
forms only read, change, destroy, need root or reach the network, and refuses what it cannot classify; reads run sealed
and their output is data; changes show "this will … / the command: …" and wait for the press. **KS3 · The system
door.** Software, services, users, time: through the system's own permission prompt with the owner present, one fixed
action per prompt, never under a standing grant. **KS4 · Grounding and "teach me".** An index of the machine's manual
pages and help texts; every option she proposes exists on this machine; DOS and Windows words mapped to Debian's,
quoting the page.

### Preview 4 and the candidate (outline)

**B5 · A quieter bar.** The owner, 28 Nov: "We could move the tray to the upper left free space to free up space
on the bottom bar. Unless you have better plans". The builder's answer: the head's upper left is inside Graphite's
window and hides behind any app in front, so the machine's state stays on the bar, made small: network, sound and
battery become one Quick Settings button (three glyphs, words in the tip, as Windows 11), one press opening one panel
with all three sections and the meters (CPU, GPU, RAM, TXT, NET) as a fourth; the window buttons get the room. In
Graphite's head, the menus start at the left edge (as a Windows app's), and Apps ⊕ leaves the head (Start does that
job: one place). If the owner says "move it", the tray goes to the head's upper left instead. *Acceptance:* at 1366
three app windows fit on the bar with Kas, HALT and the clock; one press opens network, sound, battery and the meters;
nothing the tray or the meters did is lost.

**N1 · Night is a phosphor monitor.** The owner, 28 Nov: "Remember night mode is to look like old computers that only
had orange and black / green and black monitors....but updated to 2026 but still old school modern". Night becomes a
monochrome phosphor look on a near-black ground, in two phosphors, **Amber** (the default) and **Green**, chosen under
View ▸ Appearance. Hierarchy comes from the brightness of the one phosphor, never from another hue. A selected row is
inverse video. The chrome uses a fixed-width face. Crisp 2026 rendering, with at most a faint phosphor bloom on text
and no blur or scanlines over words. Every state keeps its word and shape. Pictures stay in their own colours, since
they are content. The bar, Start, flyouts, the Explorer, the menus, her panel and cards, the board and the drop-down
terminal all follow. Day and Kasandra are unchanged. *Acceptance:* frames of Night Amber and Night Green (the window,
the bar with Start open, the terminal); every text brightness at least 4.5:1 on the ground; the Night tests on the new
truth.

**C0 · A real terminal.** The drop-down Terminal (B4) and 1.0's Terminal are not terminal devices: vim, top, less
and sudo's password prompt do not work in them. Give the drop-down a real terminal (a pseudo-terminal running the
owner's shell) that keeps what B4 built: it drops from the top edge on Win+` and Ctrl+Alt+T, over any app, and leaves
when done; DOS words still work and still show the Debian command they ran; the owner's own shell rc is untouched.
*Acceptance:* vim opens, edits and saves a file; top runs and q quits; sudo asks for its password in it; dir prints
the Debian line and runs it; Win+` hides it and gives the keys back.

**C1 · Software and updates** (find, install, remove, update, with the system door). **C2 · Printers, Bluetooth, date
and time, users, power.** **C3 · The Task Manager.** **Z1 · The live image** and its boot smoke. **Z2 · The security
review** of the authority code and the new doors, and the minimal authority tests. **Z3 · Licences**, the package's
exclusions, `debian/copyright`. **Z4 · Old rooms cleared**, the docs of a distribution, and the walk of X3's and X4's
sessions with Windows hands.

## 6. Reversals for the owner to strike

| Earlier decision | In 1.1 | Why | Preview |
|---|---|---|---|
| No key printed on screen (13 Nov) | Keys shown in menus and tips; one setting turns them off | a person switching learns keys from menus | pre1 |
| Text console start only | A graphical login as well; the console start stays | a distribution boots to a login | pre1 |
| HALT upper left (26 Nov) | HALT on the bar beside Kas's name | an app in front hides the head; the bar is above every app | pre2 |
| Apps upper right (14 Nov) | Start at the lower left, on the Windows key; the word stays "Apps" | where a Windows hand goes | pre2 |
| The tree from "This computer /" (26 Nov) | Quick access first, the root one press down | 1.0's first sight was system folders | pre2 |
| DELETE as the bin's word (14 Nov) | "Recycle Bin" on new installs; the owner's profile keeps DELETE | a capital verb reads as an act | pre2 |
| The eight menus' names | File, Edit, View, Go, Tools, Help over the same actions | the names a Windows hand knows | pre2 |
| Graphite full screen (the session) | Graphite maximised above the bar | the bar stays above every app | pre2 |
| "Outside your home: never" for Kas | System changes through the system's own prompt, the owner present | a full Linux box means software and services | pre3 |

Not reversed: no picture of Kas; Apps, never Programs; Day as the launch look; every state a word and a shape.
