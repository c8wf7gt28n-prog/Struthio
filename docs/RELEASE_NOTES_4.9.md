# Ledger & Slate 4.9 release notes: deeper

4.9 is Pass B of the two passes that finish the program. Working copies grow from one file to whole projects, and the parts built earlier work together more closely.

## Working copies of folders

**Work on a copy…** now asks whether you want a copy of a file or of a folder.

- **A folder copy** takes every ordinary file in the folder, up to 500 files and 256 MB, and keeps each one as a protected snapshot.
  - It leaves out hidden files, machine files (`.git`, caches, object files) and links, and never follows them.
  - Review lists what was left out.
- **A proposal is a list of operations:** change, add, remove. A rename is a remove and an add.
- **Review shows every operation in words,** then the line differences of each changed text file.
- **Update the original now** first checks the **whole** original folder against the snapshot the work began from. If any file changed elsewhere, nothing is touched and the changed files are named. It then applies one file at a time, each journaled:
  - a change uses the same private-temporary-then-rename step as a single file;
  - an addition never overwrites;
  - a removal happens only if the file still holds what the work began from, and its bytes stay kept.
- **This is a recoverable update across many files, not an atomic one.** If it stops part way, through a crash, a full disk or Stop:
  - each file's journal says what happened;
  - the copy says **Partially applied — review required**;
  - updating again with the same approved revision finishes the job, recognising the files already done.
- **Undo** reverses the last folder update, and only if each file still holds what the update wrote.
- **Save as a new file beside it** writes the whole proposed folder under a new name. It never overwrites.

## Merging

When the original of a working copy changed elsewhere, Review now offers **bring the outside change in**:
- Changes made only in your working copy, or only elsewhere, are both kept.
- The same change made on both sides is taken once.
- Different changes to the same lines become a conflict, written in the working copy between marker lines (`<<<<<<< your working copy` … `=======` … `>>>>>>> the original, as changed elsewhere`), for you to settle.
- A working copy with unsettled markers cannot be frozen for review.
- The working copy's version from before the merge is kept.

Merging works on one text file at a time; folders are reviewed file by file.

## Slate works on a copy you give him

On a working copy you gave Slate, Files offers **Ask Slate to work on this…**.

- **What happens:** what you write becomes an Agenda item. When it runs, Slate's brain rewrites the file as asked. His answer becomes the working copy's content, and is frozen as a revision that waits in **Waiting for you** and in Review.
- **What stays the same:** the original is never touched. Without a brain, the item waits, as plain-words items do.
- **His answer must contain the whole file.** If it doesn't, nothing changes and the item says why.
- **Limits:** text files up to about 6,000 characters, one file at a time.

## The story of a file

The Context panel for a file in Files now shows its **History**, near the top. It is built from Ledger's own records, never inferred:
- kept from a delivery;
- versions kept;
- Slate's proposals and what you decided;
- Trash;
- becoming a working copy, its frozen revisions, and its updates and undos;
- watches and Agenda items that ask about it.

## Chains, from anywhere and to the shell

- **Right-click a staC answer in the console** to carry on from it as a chain.
- **Right-click an Agenda item** that asks staC to carry on from its question.
- **then › shell** ends a chain with your own command. It runs on the console's Shell page, and the answer is a CSV file named in `$LEDGER_ANSWER`.
  - Commands you use often go in your Ledger menu file as `[shell] (Name) {command}`.
  - This is the one place a chain leaves Ledger. It is always the last step, it is shown before it runs, and Stop ends it.

## The typing bar, and the top row

**One typing bar along the whole foot of the window.** It is the only place to type commands, searches or questions in Ledger, Slate's included (Ctrl K takes you there).

| Left, under the Library | Middle | Right, under the right panel |
|---|---|---|
| **line · half · tall**: how much room the console takes | the box, as wide as the work | **Slate · staC · Kernel · Find · Shell**: who you are typing to |

- **Slate** answers in his panel on the right, whose own box is gone; meanwhile the console shows the Timeline.
- **staC, Kernel, Find and Shell** answer in the console above the bar, where answers stay.
- **A first character still jumps:** `@` staC, `/` Kernel, `?` find, `$` shell.
- **For console targets,** Tab completes and ↑ ↓ walk that target's history.
- **An operation that needs your approval** comes back into the box after the first Enter; a second Enter runs it.
- **Results and the live staC preview open upward** from the bar.
- **`? words`** finds in Files (with **show in Files** and **keep as a smart folder**), in what the Office received, among commands, and in the Timeline.
- **The other search fields are gone:** above the Library, in Files and in the Library tab. Jot it down and the Agenda's line for a new item stay, because they are for writing.

**The top row is one line:** **Ledger & Slate** in script, then the program's logo, then the path of where you are, then File · Edit · View · Tools · Help, Slate's state and Stop.
- **The path**, such as `~/Concern/Office › Files › Working copies › board`, follows the open tab. Each step takes you back up to it.
- **The first step of the path is the workspace.** Clicking it offers your other workspaces, which replaces the Office ▾ menu.
- **The logo** opens Today. It is drawn in the paper palette from `branding/logo/source.png` by `tools/render_logo.py`. To use an upgraded logo, replace `source.png` and run the tool again.
- **The magnifier is gone.** The logo takes that button's place (the release checks keep the button).
- **Files no longer repeats** its own path line.

## The logo's Easter egg

Click the logo, the rider on her war bird, to play **STRUTHIO · ARCADE**, R. A. Peddycoart's game: climb the tower of floating islands to the moon. Use ← → (or A D) to flap left and right, ↑, W or Space to flap hard, and Enter to start.

- **Where it comes from:** the arcade build from the STRUTHIO repository, version 1.8.0, copied unchanged into `games/struthio`. `FROM_REPOSITORY.txt` names the commit.
- **How it runs:** the game is JavaScript and draws with WebGPU. Ledger serves its folder, read-only, on 127.0.0.1 only, and opens it in a window of its own, run by a separate small program that uses Qt's built-in Chromium (QtWebEngine, already part of PySide6). Nothing else needs installing, and nothing is sent off the computer.
- **Ledger itself never loads a web engine,** so a game that cannot start cannot take your work with it. If its window cannot start (no 3D graphics, for instance), the game opens in your web browser from the same local address.
- **Stop and Master Stop** end the game's window. Its saves live in its own storage, not in Ledger.

## The status line is gone

The line under the work ("Ledger · Program only · Project not attached … Office workspace · Brain none yet") repeated what the path, the top row and **Needs a project** already say, so it is hidden. Its one live job, short messages such as "Saved as…", now shows in the typing bar while the bar is empty.

## Pictures in the chain menu

Each link in the chain menu has a small drawn picture, so you can see what a command will do before you read it. They are graphite lines, drawn by Ledger so they stay sharp at any size and inside the palette:

| Picture | Link |
|---|---|
| a funnel | **where** |
| arrows | **sort** |
| stacked boxes | **group by** |
| a column | **select** and the column names |
| a column with a plus | **add a column** |
| two linked rings | **join** |
| a broken ring | **missing** |
| `#` | **count** |
| Σ, x̄ and bars | **sum**, **avg**, **min** and **max** |
| `>` `<` `≥` `≤` `=` `≠` | the comparisons |
| a dot | each value found in a column |
| lines, a grid, layers, a T | **rows**, a **sheet**, **layers**, **texts** |
| a chain link | a chain you kept |

**then** and its endings are drawn in eraser pink: a console prompt, a sheet with an arrow, an eye for watch, a checked page for the Agenda, a bookmark for keep, two pages for copy, and `$` for shell. The top menus stay words only.

## Less scrolling

- **The Library fits its column.**
  - Rows are tighter.
  - Click a section's name (ARRIVE, FILES, LIBRARY…) to fold or open it. Your choice is remembered.
  - When the Library is taller than the window, sections fold themselves, bottom first (CONCERN, PROJECTS, KEEP, SLATE, LIBRARY, ARRIVE). A section you opened yourself and the one you are in stay open.
  - A folded section still shows the count that matters inside it, such as "1 to look at" or "1 for you".
- **The Context panel uses one line per fact:** a short value sits beside its label. Only long values, such as a digest or a sentence, go underneath.
- **The Agenda:**
  - Next and Waiting show their first six items, then "and N more · show them".
  - Later and Done are one line each until you open them.
  - Its rules are said once, in the Context panel.
- **Slate's conversation** keeps the latest eight exchanges in view. Earlier ones fold behind "N earlier · show them".

## This computer

**Tools › This Computer** looks at what this machine offers for confining programs, and changes nothing. It checks:
- the kernel;
- bubblewrap: Ledger runs `true` inside its fixed profile, so "verified here" means it worked just now;
- Landlock and its version;
- seccomp;
- user namespaces;
- cgroups v2 and what this session may use;
- the filesystem under Files, and the free space.

Each line says why it matters. This is the first step in the File-Management Plan's section 16. On your ThinkPad it says what the sandbox work can rely on.

## Trash is a trash can

- **In the Library:** Trash is no longer a row in the tree. It is a small graphite can at the foot of the column, above Settings. A dotted pencil stem fading down from the tree joins it to the Library, so it sits apart from the tree but still belongs to it.
  - When something is in the can, a crumpled sheet shows over its rim and the count sits on the right like every Library count.
  - Click the can to open Trash.
  - Drop files from Files onto it to move them there. This uses the same `files.trash` step as Delete, so everything stays recoverable.
- **Only in the Library:** the can lives at the foot of the Library and nowhere else. A folder of your own that happens to be called Trash looks like any other folder.

## Code hygiene

A clean-up with no change in behaviour, checked with pyflakes and vulture:

- **Unused imports:** 157 removed across 88 files in `workbench` and `tools`. Only the import statement itself was
  rewritten, and every file was checked to still compile.
- **What was kept on purpose:**
  - names another file reaches through the module;
  - deliberate re-exports in package `__init__` files;
  - imports inside a `try`;
  - module imports that may matter for their side effects;
  - the release checks in `tools/check_*.py`, which were not touched.
- **Dead code removed:**
  - an uncalled method (`quiet_commands`) and an `if True:` wrapper in `shell2`;
  - a value that was written but never read, in the console;
  - an unused constant and an unused function from the new code.
- **Left alone:**
  - the protected `sdk` (25 findings, all unused imports) and the existing tests;
  - a few unused local variables in older code, which hold the results of calls that do real work.
- **Tidy tree:** old 4.1 delivery receipts and update notes moved from the top folder to `docs/history/` (nothing
  reads them; nothing was deleted), and generated caches and an empty build folder removed.
- **Checked:**
  - pyflakes finds no undefined names anywhere;
  - every module imports, except the old Tk front end on a machine without `tkinter`, as before;
  - the staC foundation was rebuilt and verifies;
  - the focused tests and the release UI check pass;
  - every test module in the tree gives the same result before and after the pass.

## staC carries its own notes (disclosed: the staC foundation)

The staC foundation is built from Ledger's program files and from 41 written notes in `docs/` (and `AGENTS.md`). It used
to refuse to run unless every one of those notes was on disk, unchanged. Now:

- The foundation's index holds the full text of each note, and the index is bound to the foundation's manifest by its
  own fingerprint. So a copy of Ledger may leave the notes out, and staC still answers from a verified foundation.
  `seed_status` lists those notes under `carried_in_seed`.
- A note that is present must still match exactly, or staC reports the foundation as out of date, as before.
- Program files are never optional. Every `.py`, `.js`, `.json` and runtime file the foundation is bound to must be
  present and unchanged, or staC refuses to run.
- Rebuilding the foundation (`build-seed`) is a development step, and still needs every note.

This lets the runtime package leave the notes out: about 40 fewer files, with no change to what staC knows. Test:
`tests/test_ledger_backlog.py › CarriedNotes`.

## The backlog, finished

- **Confined runs.** A command can run inside a working copy's folder with no network, only that folder writable,
  limits on processor time, memory and file size, and a kill at its time limit. Master Stop ends it too. Use
  right-click › Run a command here, confined…, or `confine.run`, which needs your approval.
  - The mechanism is bubblewrap where it is installed, and Landlock otherwise. With neither, a run is refused, never run
    unconfined.
  - On this test machine every escape attempt was refused: reading or writing outside the folder, opening a network
    connection, a runaway loop and a 6 GB allocation.
- **Untrusted files are read inside confinement.** Right-click › Look inside, confined… runs Ledger's own readers on
  every file of a folder copy (a pill's, for instance) inside confinement. A damaged file is reported, never fatal.
  Tools › This Computer now has a "Confined runs" row, tried for real each time.
- **Slate changes workbooks.** Give Slate an `.xlsx` working copy and he sees it as cells (`Sheet!B3 = 16`,
  `C2 = "10k"`, `D4 = =B4*C4`) and answers with only the cells to change.
  - Ledger changes those cells in his copy. Styles, other sheets and every other byte stay as they were, and the
    workbook recalculates when it is next opened. Checked with openpyxl and LibreOffice.
  - His revision waits for your review, as with text.
  - The new `files.cells` operation keeps the version before, as `files.write` does.
- **The pill link (step 6 of docs/PILLS.md).** The same pills travel over a dedicated cable:
  - only paired computers can connect, and both sides prove who they are;
  - everything is encrypted, and a changed or replayed frame ends the session;
  - it carries pills and nothing else (list, get, put).

  The appliance only connects out (Tools › Pills › Fetch / Send over the link…). Fetched pills wait in quarantine
  (Files › Received › Pills).
- **Fixes:**
  - With no project attached, Ledger starts on Today. It no longer opens a "Needs a project" tab, which came from the
    old start trying to open a project's 3D assembly.
  - Kernel tables in the console show times as "today 11:56", "yesterday 09:12" or "28 Oct 14:03" instead of raw
    seconds. Only fields named as times are changed, and every other number stays as it is.
- **Tests:** `tests/test_ledger_backlog.py` (9) and two link tests in `tests/test_ledger_pills.py` (11 in all).

## Pills: two computers, one language of work

Ledger can now exchange work with your ordinary workstation through **pills**: signed, self-describing `.pill` files.
The full design is in `docs/PILLS.md`. The rule is "a pill asks; the computer that receives it decides".

- **On the workstation:** a small handler, `python3 -m pillkit.handler`, needs only Python and `cryptography`, not Ledger.
  It prepares a request from a project folder, reviews a result with a text diff, saves it as a new folder, or applies
  it. Apply happens only after you type yes, only if every touched file is still exactly as it was sent, and from a
  journal, so an interrupted apply can be finished (`resume`) and any apply can be put back (`undo`).
- **In Ledger:**
  - Open a `.pill` from Files, or from Tools › Pills and Paired Computers…. It is checked (signature of a paired
    computer, every hash, meant for this Ledger, not a replay), then accepted as a working copy, for you or assigned to
    Slate. Its files arrive inert.
  - The copy's original is on the other computer, so Ledger cannot change it.
  - Right-click the copy › Return as a pill… packs your findings and the changes into Files › Exports › Pills. That is
    your approval to export, and only that.
- **Pairing:** each side gives the other its card. Both screens then show the same pairing code.
- **Refused, with the reason in words:**
  - a changed byte;
  - an unpaired sender, or a pill meant for another computer;
  - a replay;
  - a request for more than inspect / analyze / propose revisions / test;
  - any attempt to lift the "no changes to originals" limit;
  - unsafe names (`..`, absolute, hidden, reserved), links, folders, encrypted entries and zip bombs.
- **Kernel:** `pills.identity`, `pills.pair`, `pills.unpair`, `pills.open`, `pills.accept`, `pills.list` and
  `pills.return`. Pairing, accepting and returning need your approval; Slate cannot call them.
- **Decisions recorded for the appliance:**
  - a kiosk Wayland compositor rather than EGLFS (Ledger needs popups, drag and drop, and the game's separate window);
  - parsers confined, because the Debian base stays fixed;
  - signed offline update pills for parser packages.
- **Disclosed (pins):** `requirements-qt.txt` now pins `cryptography==50.0.2` for the Ed25519 signatures, and a new
  `requirements-pills.txt` lists the workstation's only requirement.

## No scrolling for the last few lines

- **Snug pages.** A page that is taller than its window by no more than a quarter of the window is now framed to fit instead of scrolling. Ledger takes air out in steps: first the gaps between blocks, then the margins, then writing boxes such as Jot it down (never below a floor of 64px). Text never gets smaller and nothing is hidden. The scroll bar goes away while the page fits.
  - When the window changes size, or the page gets shorter, the page is framed again from its own spacing, so it never flickers between two states.
  - Pages that really are long, such as a big folder or a long note, still scroll as before.
- **Slate's Agenda** no longer gives a heading and a "Nothing is…" line to every empty section. The empty ones are named together on one line, for example "Empty for now: Now · Next · Waiting for you · Later · Done."
- **This Computer** is set in two columns of short entries, so the whole look fits on one screen.

## Page headings in script

The big heading at the top of each page is now in script, as "Good morning." already was. This covers Files (and each folder's name), Library, Slate's Agenda, Trash, This Computer, Investigations, Review, Needs a Project and the rest. A heading says where you are once, with grace. The words you read and act on beneath it stay in print. View › Pleasantries in script turns script off, and the headings return to plain Plex at once.

## The ledger head

The top row is styled after the head of a page in an account book:

- **Margin rules:** a pink double line stands on each column edge, the way ledgers rule their columns. The lines sit exactly where the typing box ends at the foot of the window.
- **Closing rule:** a graphite double rule closes the row, as a ledger closes a heading.
- **Left cell:** the wordmark in script, and the logo.
- **Middle cell:**
  - **The path** is written like an account heading. The steps above where you are (each one a way back up) are in small capitals, joined by a pink slash. The place itself is in bold print: it is the one word on the row that says where you are.
  - **The menus** are set like a ledger's column headings: File, Edit, View, Tools and Help in spaced small capitals.
- **Right cell:** three tally columns (cpu, mem and slate), each headed in small capitals, then the date, then Stop.
  - cpu and mem show the last minute as a pencil wash over a ruled baseline, with the current percentage beside each heading.
  - slate shows Slate's dot: a ring for no brain, half filled for working (with a count), filled for ready.
  - The date is in script, because every ledger page is dated and the date is the quiet word of the cell. Hover over it for the full date.

## The pulse, beside Stop

Slate's brain chip, the "n running" count and the Agenda's nice levels were three separate things in the top row. They are now one small monitor beside Stop:

- Tally columns (cpu, mem, slate) show the last minute of the processor and memory as pencil washes. A sparkline turns eraser pink only when it is nearly full.
- A dot shows how Slate is: a ring means no brain yet, half filled means working, filled means ready.
- Click the monitor and it opens as a menu:
  - **This computer:** processor, cores and load, memory in use, and the free disk space where Files are, then What This Computer Supports.
  - **Slate:** choose a model, talk to Slate, the Brain room, and stop the brain.
  - **Running and next:** each Agenda item, with its nice level (Now, Normal, Background) and Pause, Resume or Cancel.
  - The master Stop, at the bottom.

The monitor only reads `/proc` and the Kernel. Every change it offers goes through the Agenda's own Kernel operations.

## Folders with some depth

Folders in Files are drawn with a back and its tab, a front flap with a lit edge, and up to three sheets peeking out, one for each thing inside. An empty folder shows none. Well-known folders carry a small graphite mark:

- Exports: an arrow out
- Arrived and Deliveries: an arrow in
- Slate: a script S
- Working copies: two sheets
- Projects and code: `</>`
- Notes and Ideas: lines

## Menus, one job each

- **File** is about getting files in and out: New, Open, the Universal Viewer, Find a File, Recent, Receive Files, Work on a Copy, Save, Close, Recover.
- **Edit** is text only: undo, clipboard, find and replace, go to line.
- **View** is about places and size: Today, Files, Library, Slate's Agenda, Slate, Inspector, then **Console ▸ One Line / Half / Tall**, then reading and layout.
- **Tools** starts with **Type to ▸ Slate, staC, Kernel, Find, Shell** (Alt+1 to Alt+5, the same five words as the bar), then the Chain Menu, Ledger's own tools, Stop, and Engineering.
- **Help** starts with Getting Started and What's New, and ends with About Ledger & Slate.

## Symmetry

The Library on the left and the panel on the right always have the same width. Drag either one and the other follows. Each column is wide enough that none of its words are cut off. Everything lines up with the two columns:

- The top row: the wordmark and logo sit over the Library, the path and menus over the work, and Slate's state and Stop over the right panel.
- The typing bar: line · half · tall sits under the Library, the box is exactly as wide as the work, and the five target words sit under the right panel.
- Today: it keeps the right panel closed, so the same width stays empty on the right and Today sits in the middle.

## Look

- **Scroll bars** are eraser-pink.

## Kernel

There are three new operations, so the Kernel has 472. The command-line schemas match.

| Operation | Scope |
|---|---|
| `copies.merge` | approve |
| `files.story` | read |
| `system.supports` | read |

`copies.start` accepts a folder. `agenda.add` takes `copy`, a working copy you gave Slate.

## Tests

New: `tests/test_ledger_struthio.py` (the game is served read-only on 127.0.0.1 only; its window opens nothing else) and `tests/test_ledger_pass_b.py`. It covers:
- a folder copy that leaves out hidden files and links;
- one reviewed proposal changing, adding and removing files;
- an outside edit to any file in the folder blocking the update;
- a crash part way, then the same proposal finishing it;
- undo;
- save as a new folder;
- a clean merge and a conflict;
- Slate rewriting an assigned copy, with a stand-in brain;
- a file's story;
- This Computer staying a look;
- `[shell]` lines in the menu file.

Changed: `tests/test_ledger_paper.py` (the Slate composer test now checks that the typing bar is his composer, since his own box is gone by design) and `tests/test_ledger_working_copies.py`. It used to expect a folder to be refused. Folders are allowed now, so it checks that a FIFO is still refused instead. Special files are never copied.
