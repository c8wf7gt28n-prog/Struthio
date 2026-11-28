# Graphite 1.1

*28 November 2026. You asked for Graphite to become your full desktop for Debian: "the functionality of windows, with
the graceful class of Apple, and the freedom power of Linux", with Kasandra as its super power. Then: "You have complete
freedom. Just do a full release before I'm cut off for the week." This is that release. It brings together previews 1,
2 and 3 and Kas's command tool. What did not make it in is said plainly at the end.*

## Installing

Graphite 1.1 is Debian software: four packages in a folder repository.

- **graphite** is the program, in `/usr/lib/graphite`, on Debian's own PySide6.
- **graphite-llama-runtime** is the llama.cpp that runs Kas's model.
- **graphite-session** holds the session and its commands: `graphite-startx`, `graphite-session` and `graphite-do`.
- **graphite-desktop** is optional. It adds a LightDM login screen.

The steps:

1. Copy every file of the kit into one folder, for example `~/GraphiteKit`.
2. As yourself, run `bash JOIN.sh`. It checks every file and ends with `JOINED AND CHECKED`.
3. As root (`su -`), run `bash ~/GraphiteKit/install.sh --check` to look first, then `bash ~/GraphiteKit/install.sh`.
   Write your own home folder in place of `~`.
4. Log out and in on the console, then run `graphite-startx`.
5. Optional, and only once step 4 works: as root, `bash ~/GraphiteKit/install.sh --desktop` for the login screen.
   `START_HERE.md` has the two commands that undo it.

Over a preview, the same steps upgrade it. Your Graphite 1.0 in `~/Applications/Graphite-1.0` stays, and the new
Graphite opens the same workspace and settings.

## What is new since 1.0

### Your hands

- **Windows keys in Files:**
  - Ctrl+C, Ctrl+X and Ctrl+V copy and move files, with one Undo per paste.
  - F2 renames. Delete goes to the bin; Shift+Delete asks, then deletes for good.
  - Enter opens, Alt+Enter shows Properties, F5 refreshes and Backspace goes back.
- **Windows keys above every app:**
  - The Windows key opens Start. Win+E opens Files, Win+D brings Graphite forward and Win+L locks.
  - Win+K opens Kas's panel and Pause presses HALT.
  - Win+` or Ctrl+Alt+T drops the Terminal.
  - Ctrl+Alt+Del shows what runs, and PrintScreen saves a picture. Alt+Tab and Alt+F4 work.
- **Menus show their keys.** View ▸ Show keys turns them off.
- **DOS words** (`dir`, `cd..`, `copy`, `move`, `del`, `ren`, `md`, `type`, `cls`, `ipconfig` and more) work in the
  Terminal and the bar's line. Each shows the Debian command it ran. `del` goes to the bin with Undo, `copy` never
  writes over without `/y`, and `format` and `chkdsk` are explained, never run.

### The screen

- **One bar along the bottom, above every app:**
  - **Start** shows apps by kind, recent files, and Lock, Suspend, Log out, Restart and Shut down.
  - **The line** finds and does everything (apps, files, settings, commands, sums, recipes, "Ask Kasandra"), and every
    row says what Enter will do.
  - **The open windows**, Graphite first.
  - **Kas** with her state word and HALT.
  - **The tray:** network, sound and battery, each with its own panel, plus the meters.
  - **The clock**, with the month.
  - Graphite opens maximised above the bar.
- **The Explorer:**
  - Quick access first, then the Desk, then This computer with System (C:).
  - List, Icons (thumbnails) and Board (1.0's living desktop) views.
  - An address field that takes a typed path.
  - Recycle Bin on new installs; your profile keeps DELETE (Tools ▸ The bin's name).
- **File, Edit, View, Go, Tools, Help,** over every action of 1.0's eight menus. The old → new table is in
  `RELEASE_NOTES_1.1_pre2.md`.
- **The details pane** (Alt+P): a preview, the facts and the connections of whatever is selected.
- **One line, not two:** the window's foot is gone once the bar stands. Line, Search and Web are the bar's line, Log is
  View ▸ Log (Alt+6), and the meters are in the tray.
- **A Terminal that drops from the top edge** over any app, and leaves when done.
- **Command…** on a file's right-click (and Ctrl+.) shows the exact command behind Open.
- **Less chrome:** the window's own furniture takes 115 px of height at 1920x1200, down from 187.

### Kas

- **On the bar:**
  - Her state as a word and a shape: QUIET, WORKING, NEEDS YOUR WORD, STOPPED, HELD, DONE.
  - **HALT beside her name.** It stops all of her work and nothing else; RESUME restarts nothing by itself.
  - Her panel slides from the right edge over any app.
  - When something waits for you, a card rises from her chip, and it never takes your keys.
- **Her voice:** sharp, sure, dry, never bluffing.
  - Short sentences, and never "trust me".
  - "Done, verified" only where the records prove it; "Not verified. Here is what I checked." otherwise.
  - Refusals in plain words, with what to do.
- **Her forty recipes** for the everyday jobs on a Linux box: big files, free space, duplicates, pictures, PDFs, zip,
  backups, rename many, sort Downloads, what uses memory, updates (read only), disk health, and more.
  - Reads run at once.
  - A change shows exactly what it would do, runs only on your press and only if nothing changed since you saw it, is
    checked on disk afterwards, and has Undo.
  - What cannot be undone says so and asks twice.
  - Your own recipes go in `~/.config/graphite/recipes/`.
- **Her command tool:** "run: …" in her line or the bar's line.
  - Any command as a program and its words, never a shell string.
  - About 150 programs are known, and each form is classed as read, change, destroy, root or network.
  - Reads run at once inside a seal: no network, only the named paths readable, and nothing of yours writable. Their
    output is data.
  - A change shows "This will … / The command: …" and waits for your press. It is checked afterwards and has Undo.
    `rm` goes to the Recycle Bin.
  - Pipes, `;`, `&&`, `$( )`, redirection and unknown programs or flags are refused in plain words, with the exact
    line shown.
  - A command needing root is refused: in 1.1 she makes no system changes.
- **Her rules did not move.** The model proposes; the desk disposes. Grants are named in plain words and enforced at
  every step. Kas never runs a change as her own step: you press, every time.

### Under the hood

- **The test suites run green again.** 1.0 was built with no tests, by your rule. Tier 0 is at 0 failing in Day and
  Graphite, and tier 2 has two named failures.
- **Faults fixed:** sixteen real program faults, among them a crash when a tab's icon was freed, HALT's size, the
  window strip at 1366, and a quick Ctrl+Z after a paste in the Explorer finding nothing to take back.
- **The guides** use the new words, and a test keeps them so.

## What was tested, and what was not

By your rule, tests were minimal: each piece has its own test file, and at each merge the seed was rebuilt and the
window opened offscreen in all four looks. On the final tree:

- **The new parts' tests:** 164 tests across them pass on a copy.
- **The release check** passes on the exact commit the kit was cut from.
- **The packages:** built with dpkg-deb, and installed in a clean Debian 13 chroot that held the 1.0 System set
  (preview 1).
- **On a virtual screen:** the bar, Start, Kas on the bar and the Terminal were run with real key presses, under a
  stand-in window manager.

Not exercised: real Fluxbox (whether apps stay clear of the bar, and Start's key timing); the LightDM login screen; any
of Kas's new words, recipes or commands with a real model; anything on your ThinkPad. Your evening is the first real
proof.

## What 1.1 does not do yet

These were being built when the week's limit came near. They were paused, their work saved, and they come in 1.1.1:

- **The system door:** installing and removing software, services, the clock, users, and updates, through Debian's own
  password prompt with you present, one fixed action per prompt. Until then, Kas makes no system changes, and her
  command tool says so.
- **A real terminal in the drop-down.** Today it is not a terminal device, so vim, top, less and sudo's password
  prompt don't work in it. Use the text console (Ctrl+Alt+F2) for those until 1.1.1.
- **Grounding:** an index of your machine's manual pages, so every option she proposes is checked against your
  version and quoted, and "teach me" answers from the page.
- **A quieter bar:** network, sound and battery as one Quick Settings button, freeing room for window buttons.

And from the distribution plan, not yet begun:

- printers, Bluetooth, and date and time pages;
- a Task Manager;
- a live image to boot from;
- an independent security review of every door Kas has;
- a pass over the package licences;
- the old 1.0 rooms cleared away.

Smaller items:

- **On the bar:** no Pin and no drives in the tray.
- **Command… is not yet everywhere:** it is missing on Start's tiles and on the board.
- **Kas's words:** her older phrase tables are not yet in her new voice.
- **Tests:** two named tier 2 failures remain (the Ctrl+Z race the third was is fixed).

## Reversals for you to strike

Each goes against something you decided earlier. Say "strike N" and it goes back.

| # | Earlier | In 1.1 |
|---|---|---|
| 1 | No key printed on screen | Keys shown in menus; View ▸ Show keys turns them off |
| 2 | Text console start only | A graphical login as well, optional; the console start stays |
| 3 | HALT upper left | HALT on the bar beside Kas's name |
| 4 | Apps upper right | Start at the lower left on the Windows key; the word stays "Apps" |
| 5 | The tree from "This computer /" | Quick access first, the root one press down |
| 6 | DELETE as the bin's word | Recycle Bin on new installs; your profile keeps DELETE |
| 7 | The eight menus' names | File, Edit, View, Go, Tools, Help |
| 8 | "Outside your home: never" for Kas | Coming in 1.1.1: system changes through the system's own prompt, with you present |
| 9 | Graphite full screen | Graphite maximised above the bar |
| 10 | The foot's line with five names (0.5.3) | No foot: the bar's line, the drop-down Terminal, Log under View, the meters in the tray |

Not reversed: no picture of Kas; Apps, never Programs; Day as the launch look; every state a word and a shape; her
authority rules.

## Your evening

1. Install (above), then run `graphite-startx`.
2. **The bar.** Open LibreOffice from Start with the Windows key. Is it above the bar? Press the clock, the battery,
   then the sound.
3. **The line.** Type `calc`, `12*7`, `dir`, `control panel` and `free space`. Each row says what Enter does.
4. **The Explorer.** Open Downloads, sort by size, switch to Icons in Pictures, and press Alt+P.
5. **The Terminal.** Press Win+`, type `dir` and `cd..`, then press Win+` again.
6. **Kas.** Ask her: "sort my downloads by kind". Read her list, press Run, check, then Undo. Then ask
   "run: df -h", and "run: ls ~ | wc -l" (that one is refused, and she says why).
7. **HALT.** From LibreOffice, press Win+K, then Pause. RESUME is on the bar.

Whatever differs from the page is a result. Send it, with a photo if it's on screen.
