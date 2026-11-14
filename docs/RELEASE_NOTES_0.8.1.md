# What's new in Graphite 0.8.1

November 14, 2026. Guide → What's New opens this page. The 0.8.0, 0.7.0, 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1, 0.5.0,
0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came
before.

## The right-click: short, with pictures, and it chains

"Also right click was too complex. We need to make its power easy to use and chain/pipe. With right click icons too."

**One short shape everywhere.** Every right-click menu now has the same shape:

- at the top, the thing itself: its kind's glyph, its name and what it is;
- up to four usual actions for that kind of thing;
- **Then ›** when the thing has a line, or **Start from ›** on an empty place;
- **More ›** with everything else, in named groups: Open and show, Change it, Look into it, Send and keep, Edit and
  copy, This working copy, Make and arrange, As a line.

A file's menu is six rows; it was 25 rows, taller than a 1366 × 768 screen. Nothing was taken away to make it short:
every row the old menu had is under More, or is done by the line panel, and a test walks the new menu to find each one.

The usual actions, for example:

| Right-click on | At rest |
|---|---|
| A file | Open · Ask Stacy (Kasandra) about this · Rename · Move to Trash |
| A folder | Open · Rename · Copy path · Move to Trash |
| Two files | Compare these two (or Compare revisions) · Move to · Copy paths · Move to Trash |
| Selected words | Bold · Italic · Move to notes · Ask |
| A sheet in the Field | Open · What can be done · Doubt it · Ask |
| A job | Inspect output · Pause or Resume (whichever applies) · Stop · Show in Jobs |
| An empty place in Files | New folder · Import · View as · Refresh |
| Today | New Idea · New Project · Import · Inquiries |

Only rows that can act now are at rest. A row that cannot is under More, dim, and its tooltip says why; the word
"unavailable" is no longer printed.

**Graphite's own glyphs on every row.** The right-click wears the same drawn glyphs as the menus across the head, at
the size they were drawn for. Eight are new: trash, pause, filter, sort, count, count by, watch and trace. In Kasandra,
Then and the line's own steps are royal purple, and Move to Trash and Discard this draft are red, like the Trash can.

**Then ›: the line panel.** Then opens a panel beside the menu with the thing's line on its royal-purple slab, how many
rows it gives, the first few, and how many steps the line has left. It reads once, when it opens. After that every
choice is counted from that one read, so you see what a step gives before you take it:

- **Keep rows where ›** a column › a value, each value with the rows it keeps (is mA, 2 rows; at least 110, 3 rows);
  Another value… puts the line so far in the writing line for you to finish;
- **Sort by ›** (left out on numbers written as text, which would sort 110 before 12), **Count**, **Count by ›** a
  column, **First ›**, **Read it as ›** (rows, headings, layers…), and **Back a step**;
- then **Show it** (runs it; the answer is in the working area), **Put it in the writing line**, **Copy the line** and
  **Copy the rows** (as CSV).

A line gives at most 200 rows: above that, Show it says so and First offers 200. A file whose name has a space now has
a line too. A reviewed sheet in the Field (07 Bench readings) is read by its reviewed rows: 4 rows, then two steps to
"where unit is mA, count" gives 2.

**Stop asks first.** Stop on a job or on Agenda work opens a small screen that says why it asks (what it stops cannot be
put back), with **Stop it** and **Leave it**. Nothing is stopped before Stop it, and the job is read again at that
moment: if it moved on meanwhile, nothing is done and you are told.

**Nothing scrolls, nothing prints a key.** Deeper screens open beside the menu and replace each other in place, with
Back at their top: never more than two popups. No screen is taller than the window, at 1366 × 768 or 1920 × 1200 (More
folds its largest group into one row only on a short window). No key is printed on any row, caption or tooltip of the
right-click, the Field's letter captions included; the keys still work.

**Opening the menu reads nothing.** Kept versions of a file are read only when Compare with a kept version opens.

Three questions are yours to decide; until then these are the defaults:

1. Rename, Move to and Copy to have no Undo yet (their dialog is the confirmation).
2. Nothing leaves the right-click, even rows that do the same as another (they are under More).
3. The glyphs show whatever Rules ▸ Buttons is set to.

Not in this release (the plan's second session): Save as a sheet, Watch it, Add to the Agenda and Keep as a word as
endings of a line, through her hand with its Undo; To a command (which will ask); the steps Total by, Only some
columns, Add a column and Match with a table; the right-click on the console's answers, the Agenda's rows and a
viewer's page; and the right-click section of the desk guide (GRAPHITE_DESK.md). The daily guide's section is new.

## Prompt, Apps, a red arrow, and a tree with some light in it

"Let's lose the term poem … Maybe just prompt." "We'll change the name programs to apps. APPS." "Maybe the send arrow
… red … the trash can being red." "Bring some life or energy into that left-hand tree column."

- The writing line's empty words say **prompt**.
- **Programs** is now **Apps**, in the head, the list, the Field's face and the words that point to it.
- In Kasandra the send arrow and the Trash can are **red**.
- The left trees breathe a little: a soft light under the path to the current row and under the row the pointer is on,
  stilled when Reduce motion is on.
- In Kasandra the tree is a line of **telephone poles**: each row hangs from a crossarm by a drop wire with its
  insulators, and the live path carries a thin lit riser.

## The model's memory rules (for the 35B)

The campaign's resource cases found where the memory rules disagreed with your spec and with each other. All of them are
decided now, and the resource set of the campaign is 22 of 22 plain passes:

- **Auto takes your 35B model at 39 GiB available.** Auto accepts a model when its estimate, the 2 GiB foreground
  reserve and 4 GiB of headroom fit in what is available, and budgets 65% of available, never below the estimate nor
  above 32,768 MiB. Your model at 4,096 context needs 32,157 MiB (31.40 GiB) available; a refusal now says its numbers.
- **The headroom stays.** After submit, admission and launch still ask for the estimate with its headroom (30,109 MiB at
  39 and 40 GiB), so memory that falls after you asked makes the model wait instead of starting with 2 GiB to spare.
- **One rule.** Admission, the model's configuration and the launch check use the same rule, so a model admitted is not
  refused at launch for the same numbers. The old limit of 80% of available is gone.
- **A handover waits for memory.** When one model replaces another, the launch waits up to 8 seconds for the old one's
  memory to come back; if it does not, nothing has started, and the previous model is restored when there is room.
- **Unmeasured memory.** If installed memory cannot be read, the full 2 GiB reserve stays, and a request whose reading is
  lost fails after 30 seconds, saying why.
- **Ready means a reply.** A model whose test reply is empty is not Ready (also when restoring the previous one); a worker
  that gives less context than selected is refused (on Vulkan it is retried once on the processor).
- **A hold holds.** While work is held, queued requests stay queued and continue from the right step on release.
- **One reading.** Admission and the worker's guard read memory the same way, the cgroup limit included; after a memory
  stop during a handover, the model's status keeps saying so until a model is Ready again.
- **Simulated runs say so.** The campaign's fixture runtime records SIMULATED_WORKER_LOAD_LOG; a real run records
  PINNED_WORKER_LOAD_LOG as before.

## Packaging

The MANIFEST.json kept in the repository no longer lists the session's own working copies (packaging leaves `.claude`
out). The 0.8.0 kit was not affected: the kit is packaged from a clean export, and the installer restored it file for file.

## What is not done

- Nothing later than 0.4.6 has run on the ThinkPad. These notes describe what the checks here show; the first real run
  of the model rules and of the right-click is yours.
- The second session of the right-click (above).
