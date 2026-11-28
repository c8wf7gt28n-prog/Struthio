# Graphite 1.1 preview 3: her recipes, one line, a drop-down Terminal

*28 November 2026. The third preview on the way to Graphite 1.1. Preview 3 is where Kas starts to reach the whole box.
It brings her recipes, one line instead of two, and a Terminal that drops over any app. Two more of her pieces, the
command tool and the system door, were being built when a usage limit stopped them; they come in preview 4. Install
over preview 2 the same way: `bash JOIN.sh`, then `bash install.sh` as root.*

## What is new

**Her recipes: forty everyday jobs on the whole box, safely.**

- **Finding things:** find big files, see what takes the space, find duplicates, what changed since yesterday, recent
  downloads, find a file by its name or by its words, old files, empty folders, what kinds of files a folder holds,
  and a folder's size.
- **Pictures and PDFs:** convert pictures, resize them, make them small for email, make thumbnails, merge PDFs, split
  a PDF, and count a PDF's pages.
- **Folders and the bin:** zip a folder, unzip, list a zip, rename many, sort Downloads by kind, back up a folder to a
  drive, see what's in the bin, empty the bin.
- **The machine:** what uses memory, what uses the processor, is the system up to date (reading only), disk health,
  which apps start with the session, about this computer, the battery, the network and failed services.

Every recipe follows the same rules:

1. **Reads run at once.**
2. **A change shows its dry run first,** listing exactly what it would do (which file goes where), then waits: **Run
   it (your press)** or **Not now**.
3. **It runs only on your press, and only if nothing changed since you saw it.** If something did, she plans again and
   shows you.
4. **It's checked afterwards** ("✓ Done and verified … 8 files read back at the new place, the same file, the old place
   empty"), and **Undo** puts it back.
5. **What can't be undone says so before the press.** Emptying the bin asks twice.

Kas never runs a change as her own step, and no standing grant runs a recipe's change: you press, every time. HALT
holds a recipe between files. Recipes show in the bar's line ("Recipe: Free space in Home, Enter shows what it would
do"), in her talk and NEXT STEPS, and as a list when you ask for her recipes.

With no model, her dictionary picks the recipe from your words and asks one question if something is missing. With a
model, the model picks a recipe by its number and may fill its blanks only with your own words. You can write recipes
of your own as small files in `~/.config/graphite/recipes/`; a broken one is refused with the reason.

**One line instead of two.** Once the bar stands, Graphite's window has no foot. Everything the foot did now has one
home:

| The foot in 1.0 and previews 1 and 2 | Now |
|---|---|
| Line, Search, Web | the bar's line (it also has "Search inside files…" and "Search the web…") |
| Terminal | the drop-down Terminal (below) |
| Log | View ▸ Log (Alt+6), with its own filter |
| The meters (CPU, GPU, RAM, TXT, NET) | one tray item on the bar ("CPU 30 %"); each row opens the same card as before |

Without the bar (for example in a plain X session) the old foot stays.

**A Terminal that drops from the top of the screen**, over any app, on **Win+`** or **Ctrl+Alt+T**. It is your shell,
in your Files folder. DOS words work (`dir` shows the `ls -l` it ran). Esc clears the line. The same key, or `exit`,
puts it away and gives the keys back to the app you were in.

**Command…** sits above Properties in Files' right-click, and on **Ctrl+.**. It shows the exact command Open runs for
that file, and the file's Graphite line, with Copy and "Put it in the line". Nothing is hidden.

**Keys from any app:** Win+K opens her panel, and Pause presses HALT (never RESUME).

**The test suites run green again.** Tier 0, the quick tier, is at 0 failing in Day and Graphite. Tier 2 has three
failures left, each named:

- her column's Review width;
- the side panes not shrinking back at 1366 after a larger window, in Day and Night;
- one Ctrl+Z test that failed once under load.

A program fault was fixed along the way: HALT's size was measured for the wrong height. Eight current guides now use
File, Edit, View, Go, Tools, Help, the bar, Start, Quick access and Recycle Bin, and a test keeps them so.

## What was tested, and what was not

- **Their own tests:** recipes (15), one line (11) and the guides' words (12).
- **On a copy of the merged tree:** 97 tests of all the new 1.1 parts pass.
- **The recipes on an invented Home:** 38 of the 40 ran and were verified. The network recipe needs `ip` (package
  iproute2), and the failed-services recipe needs systemd. Neither is on the build machine; both refuse in words here.
- **On a virtual screen:** the Terminal over an app and back, Win+K and Pause, under a stand-in window manager.

Not exercised: real Fluxbox; any recipe or her words with a real model; anything on your ThinkPad.

## What preview 3 does not do yet

- **The drop-down Terminal is not a real terminal device**, just as 1.0's Terminal wasn't. Programs that draw the whole
  screen (vim, top, less) and sudo's password prompt don't work in it. Use an xterm for those until a real terminal
  comes, planned for preview 4.
- **Coming in preview 4:**
  - **The command tool:** any command as plain arguments, classified as reading, changing, destroying, needing root or
    reaching the network, and refused when it can't be classified.
  - **The system door:** software, services, the clock and users, through Debian's own permission prompt, with you
    present.
  - **Grounding:** her answers quoted from this machine's manual pages.
- **Command… is not yet everywhere.** It works in Files, but not on Start's tiles, the board's tiles or the left pane.
- **Recipes:** there are no "pictures to PDF" and no installing updates (that's the system door).

## Reversals for you to strike

One new reversal (10) is in this preview. Say "strike 10" and the foot comes back.

| # | Earlier decision | In 1.1 | Why |
|---|---|---|---|
| 10 | The line at the window's foot with five names: Line, Terminal, Search, Web, Log (0.5.3, which you asked to keep building) | No foot: the bar's line, a drop-down Terminal, Log under View, the meters in the tray | the bar's line and the foot did the same job; one place for each thing |

Reversals 1 to 9 from previews 1 and 2 still stand for you to strike.

## Your test, if you have twenty minutes

1. Install over preview 2. Log out and in, then run `graphite-startx`.
2. Press Win+`. The Terminal drops. Type `dir`, then `cd..`, then `exit`.
3. In the bar's line, type `free space`. Enter shows what the recipe would do.
4. Ask Kas: "sort my downloads by kind". Read her list. Press Run, check Downloads, then Undo.
5. Right-click a file in Files, choose Command…, and see the line behind Open.
6. From LibreOffice, press Win+K for her panel, and Pause for HALT. RESUME is on the bar.

Whatever differs from the page is a result. Send it, with a photo if it's on screen.
