# The Living Desktop

*Graphite 1.0. Built, not tested: by the owner's rule nothing in 1.0 has been through a test, and nothing of it has run on
the ThinkPad yet. Where this page says what you see, it says what was built and seen working on the build machine, with
no screen and with stand-ins for the USB drive, the sound, the Wi-Fi and the battery. The first real proof is your first
evening (Guide ▸ Your First Evening with 1.0).*

Graphite is the whole desktop: the session, your files, your apps, the machine, and Kasandra (Kas), on one screen. With
no model loaded, everything on this page works. Her own page is Guide ▸ Kasandra, the Ghost in the Shell.

## The screen at a glance

- **The head**, the session and the authority: HALT upper left; the menus Work, Revise, Tools, Arrange, Commands, Rules,
  Properties and Guide; Apps ⊕ upper right.
- **The left**, where things are: the tabs Files, Machine and Settings; the Desk drawer of records; DELETE at the foot.
- **The centre**, the thing, what it is connected to, and working on it: the board, the working view, tabs and the split.
- **The right**, who works with you: Kasandra's column.
- **The foot**, the computer's own line and its vital signs: Line · Terminal · Search · Web · Log, the writing line, and
  the meters CPU GPU RAM TXT NET.
- **The dock**, in the dedicated session: a slim band above everything, with a Graphite entry and the windows of your
  apps.

Nothing lives in two places. Kas is spoken to in her column; the foot is the computer's line.

## The session

- **Graphite is the session.** Fluxbox runs hidden underneath for the whole session and you should never need it. If
  Graphite's window ends unexpectedly, the session starts it again after a short wait (2 seconds, then 4, then 8, at most
  30), up to three times in a row; after that it returns to the text console with a plain message. Your apps stay open
  meanwhile, because each app starts in a session of its own.
- **The dock.** A slim band across the top of the screen, above every app: the Graphite entry always brings Graphite back;
  each open app window stands there with its icon and title, the active one marked. One press brings a window forward; a
  right-click minimises it or asks it to close (the app may ask to save; nothing is forced). Where there is no window list,
  the strip stays away and says so.
- **The session group**, at the foot of the Work menu: Lock, Suspend, Log out, Restart, Shut down, Return to Debian. Lock
  starts the system's screen locker; your password is typed into it, never into Graphite. Suspend always locks first, then
  puts the computer to sleep, and waits until a file Kas is writing is finished. Before Log out, Restart, Shut down or
  Return to Debian, Graphite names the apps still open and asks each to close politely; it never kills one.
- **Notifications** from your apps appear quietly at the foot of Kasandra's column (they never take your keyboard) and are
  kept in Log.
- **The system's own permission prompts** (a password asked for by the system) appear inside the session and are answered
  there.

## Apps ⊕

- **Apps** (upper right) lists what is installed on this computer, from the apps' own desktop entries, by kind, with their
  own icons and a search line. Graphite's own rooms stand under their own heading. **⊕** beside it puts any app, or a
  command of your own, on your list.
- Every app starts in a session of its own, never through a shell, so it stays open if Graphite starts again.
- **Open with** (a file's right-click, or the viewer's Open with…) lists the apps that take that kind of file, the default
  first. *Always open PDF files with this* (and the same for any kind) sets the default in your own settings, and it is read
  back before it is said to be done.
- Large apps (Firefox, GIMP, KiCad, Blender, Godot) are not shipped with Graphite: it finds whatever you install.

## Files: the whole computer

- The Files tab starts at **This computer /**. **Home** (your home folder) is open and chosen when Graphite starts;
  **Drives** stands right under it (USB sticks, cards and discs). Every other folder your account can read is one press
  away. The system's own pseudo-folders (/proc, /sys, /dev, /run) are shown but never read. Names that start with a dot
  appear when you turn on **Show hidden** in the tab's header.
- Graphite's own workspace is a folder in Home like any other, marked with Graphite's sign. Its records stand in the
  **Desk** drawer: the concern, its sources, sheets, calculations, findings and questions.
- In Home you can open a file in its app (its saves are recorded as revisions), rename it, move it (also by dragging it
  onto a folder), make a new folder beside it, and delete it, each with Undo.
- **DELETE**, at the foot of the left column, is the system's own bin, shared with your other apps: a file deleted from
  your home goes there with where it was and when, DELETE lists it under *From your home*, and restore puts it back, never
  over another file.
- A file renamed or moved, by Graphite or by another app, stays the same object: its new name shows in the tree, on the
  board and in the breadcrumb.

## The Machine and Settings

The Machine tab has five rows, each opening its page in the centre. Every state is said as a word (MOUNTED, CONNECTED,
IN USE, MUTED, PRIMARY), never by a colour alone. Where a service is missing, the row and the page say "not available on
this computer" and why.

- **Storage:** USB drives and cards: mount, open in Files, unmount, eject safely. "safe to remove" is said only once the
  drive has really been released.
- **Power:** the battery and the mains.
- **Network:** on or off, the Wi-Fi networks, join and disconnect. A Wi-Fi password is typed into Graphite's page once and
  handed to the system's network service, which keeps it; Graphite never stores it.
- **Sound:** volume, mute, the output.
- **Screens:** which screens, their modes, the primary one, mirror or extend. A change goes back by itself after 15
  seconds unless you press Keep.

**Settings ▸ This computer** reaches the same things as settings: default apps, sound, screens, network, power, the
session and notifications, beside Graphite's own settings.

## The centre: the bulletin board

- **Select something** in Files, in the Desk drawer or in a search result, and it becomes the focus of the board: the large
  tile in the middle, with what is connected to it around it on rings (its sources, the revisions of a limit, the
  calculations made from it, the findings about it, open questions, pages that quote it). Select a tile and the tree opens
  its folders to it without closing the others.
- **A tile** says, on its first line, its kind and its state word with its shape (■ CURRENT, ■ SUPPORTED, — ARCHIVED,
  ⊘ REFUTED, □ OPEN); then its title, the basis of its link ("reviewed from page 1, version 1") and its source. A file open
  in another app says so (▣ OPEN IN GIMP, for example).
- **Wires.** A solid wire is *recorded*: the records say so. A dashed wire is *possible · not verified*: guessed from the
  same component named, the same words, or use together. Click a wire and it says why it is there ("Used 300 mA from Rail
  Demo bench readings, version 2, to calculate settled power"). A possible link becomes recorded only by your word.
- **Size is relevance**, to the focus and to what you are doing now (the task in her column, or your last request). There
  are four sizes and they stay put while scores wobble: a small change never moves a tile. Material at the edge is grouped
  as "and 12 more", which opens. Right-click a tile for **Why am I shown?** (the reasons in words), **Pin** ("pinned by
  you": drawn large, first), **Turn down** (put with the group at the edge, its link kept; Turn up again undoes it) and
  **Open beside**. Truth, confidence and authority keep their own marks: a large tile is relevant, not true.
- **The centre bar**, one bar at every depth: Back, Forward and the breadcrumb (where you are); on the board, its counts
  ("7 recorded · 3 possible, not verified") and **Whole desk**, the whole desk as sheets with what feeds what.
- An empty board says what to do: "Select something on the left; what it is connected to appears here." A tile with no
  links says why.

## Opening and working

- One press focuses; a double-click opens the object's working view in the centre (a sheet, a page, a calculation, a
  reference, a picture, a question, a text). The centre bar then reads: Board, Find, zoom, Undo, Redo, Save, Save and
  Return, Full program, Split, Close.
- Save writes. Use Save and Return to save, close the view and come back to the same board at the same zoom; what
  depended on your change is marked for a recheck. Closing with unsaved changes asks: Save, Don't save or Cancel.
- If another app saves a file you have open, Graphite notices at once: an untouched view reloads and says so; an edited one
  offers Compare, Keep yours, or Take the one on disk.
- **Full program** opens the file in its default app. When that app saves, the new revision is recorded (checked on disk)
  and the board marks what rested on the earlier revision for a recheck.
- **Back and Forward** return you to exactly where you were: the focus, the board's zoom, the place in the document.

## Tabs and the split

- What you open stays open as a named working tab, and an object is never opened twice.
- **Split** (on the centre bar, on a tab's right-click, as a tile's Open beside, or by dragging a tab or a tile onto the
  empty half) shows two views side by side, stacked on a narrow screen. The pane you click in is the one in focus: it
  drives the tree's highlight and Kasandra's "this". The other keeps its place and says quietly "Beside · another object".
  **One pane** brings them together and keeps every tab.

## The foot: the computer's line

- The chooser reads **Line · Terminal · Search · Web · Log**. **Line** is the default: a Graphite line (`this | count`,
  where "this" is what is in focus), an operation by name (`/files.list`), or an address (it opens in this computer's
  browser). Words that read
  as a request to Kasandra are not run: the line offers **Ask Kasandra →**, which moves them into her ask line and sends
  them there.
- **Terminal** is your account's own shell. **Search** finds files and their words across the workspace, the records,
  settings, commands and the timeline. **Web** opens addresses in this computer's browser. **Log** shows the events and the
  network.
- **The meters**, as words and numbers: CPU, GPU, RAM, TXT and NET. NET reads ● online, ⊘ offline, ◌ not known, or
  ⇣ "Kas: <site>" while her fetch runs. The GPU meter's card leads to the Brain room, where her model is chosen.

## HALT

Upper left: the green triangle and the word **HALT**. One press holds all of Kasandra's managed work at once (her tasks,
her hand, her model's answers, her sandboxes, her fetch) and says in her column what it stopped. It never stops the
desktop, your apps or Graphite's own jobs. While held it reads **RESUME**, the triangle turned to ▶; RESUME lifts the hold
and restarts nothing by itself.

## Looks

**Day** is the launch look: light and calm, green for what is live, blue for the wires, the rings and what is selected.
**Night** is Day's dark twin. **Graphite** and **Kasandra** stay as characterful alternatives in the same layout.
Choose in Arrange ▸ Appearance. In every look each state keeps its word and its shape, so no colour has to be told
apart. No picture of Kasandra appears in any look.

## What 1.0 does not do, said plainly

- Nothing is tested (the owner's rule). Only the ThinkPad can show the dock on a real screen, real USB drives, Wi-Fi,
  sound, suspend and lock, the system's permission prompts, the Radeon and the 35B's speed.
- The split is not restored at the next start (its tabs are). No encrypted drives; no enterprise or hidden Wi-Fi.
- The older rooms (Changes, Continuing work, Exchange & deployment, the Project Desk, the Field) are still there, under
  Arrange; the board is the centre's home.
